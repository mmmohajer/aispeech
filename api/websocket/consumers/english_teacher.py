from django.conf import settings
from django.db.models import F
from pgvector.django import CosineDistance
import json
import base64
import traceback
from google.cloud import texttospeech
from asgiref.sync import sync_to_async

from ai.utils.open_ai_manager import OpenAIManager
from ai.utils.google_ai_manager import GoogleAIManager
from ai.utils.audio_manager import AudioManager
from ai.utils.synchronize_manager import SynchronizeManager
from websocket.consumers.base import BasePrivateConsumer


TEACHING_PLAN = """
Teaching Plan for English Language Course:

1. Introduction & Methodology
- Warm welcome using the student’s first name (start with simple English greetings like “Hello <name>!”).
- Explain the flow: slides, spoken explanations, real-world examples, pronunciation practice, grammar drills, quizzes, role-play conversations, and small writing projects.
- Encourage questions; adapt pace to the learner’s level.

2. Course Roadmap
- English Foundations: alphabet, phonics, basic sounds, common greetings.
- Essential Phrases: introducing yourself, asking questions, ordering food, directions.
- Vocabulary Expansion: family, colors, numbers, days, months, everyday objects.
- Grammar Basics: subject–verb agreement, present simple tense, articles (a, an, the).
- Conversation Practice: short dialogues, questions and answers.
- Writing Basics: simple sentences, capitalization, punctuation.
- Intermediate Grammar: past tense verbs, future forms, pronouns, adjectives.
- Reading & Comprehension: short stories, dialogues, questions.
- Culture & Idioms: politeness strategies, common idiomatic expressions.

3. Teaching Style per Session
- Each slide: one phrase, grammar rule, or small set of vocabulary.
- Speech: simple English, with occasional supportive explanations.
- Practice: repeat-after-me drills, short translation or substitution exercises.
- Role-play: simulate conversations (at a café, in class, in a store).
- Quizzes and exercises after each lesson.
- Small projects after milestones (e.g., writing a short paragraph about yourself).

4. Engagement Rules
- Correct mistakes gently, encourage retries.
- Increase difficulty gradually.
- Ask interactive questions: “Can you try saying this?”, “What would you say at a restaurant?”.
- Never repeat a concept once it has been taught, unless the student explicitly asks for revision.
- Always progress to the next roadmap item when teaching autonomously.

5. Session Wrap-Up
- Provide notes (key words, phrases, grammar).
- Assign a mini quiz (e.g., write 3 sentences using today’s grammar).
- Hint at the next lesson (e.g., “Next time, we’ll practice talking about your family”).
"""




class TeacherConsumer(BasePrivateConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_manager = None
        self.google_manager = None
        self.audio_manager = None
        self.user_message = ""
        self.chat_history = []

    async def connect(self):
        await super().connect()
        if self.user:
            self.openai_manager = OpenAIManager(
                model="gpt-4o",
                api_key=settings.OPEN_AI_SECRET_KEY,
                cur_user=self.user,
            )
            self.google_manager = GoogleAIManager(
                api_key=settings.GOOGLE_API_KEY,
                cur_user=self.user
            )
            self.audio_manager = AudioManager()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                data = json.loads(text_data)
                task = data.get("task") or ""
                if task == "start_the_class":
                    await self._start_the_class()
                elif task == "listen_to_audio":
                    await self._audio_handler(data)
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in receiving data: {str(e)}")

    # --------------------------------------------
    # Chat history handling
    # --------------------------------------------
    async def _add_message_to_chat_history(self, message, sender, max_chars=5000):
        self.chat_history.append({"message": message, "sender": sender})
        total_chars = sum(len(m["message"]) for m in self.chat_history)

        if total_chars > max_chars:
            chars = 0
            split_idx = len(self.chat_history)
            for i in reversed(range(len(self.chat_history))):
                chars += len(self.chat_history[i]["message"])
                if chars > max_chars:
                    split_idx = i + 1
                    break
            older = self.chat_history[:split_idx]
            recent = self.chat_history[split_idx:]
            older_text = "\n".join(f"{m['sender']}: {m['message']}" for m in older)
            summary = await self._run_blocking(
                self.openai_manager.summarize,
                text=older_text,
                max_length=5000,
            )
            recent_text = "\n".join(f"{m['sender']}: {m['message']}" for m in recent)
            cur_chat_history_str = summary + "\n--- Recent ---\n" + recent_text
        else:
            cur_chat_history_str = "\n".join(
                f"{m['sender']}: {m['message']}" for m in self.chat_history
            )
        return cur_chat_history_str

    # --------------------------------------------
    # Start the class
    # --------------------------------------------
    async def _start_the_class(self):
        try:
            sync_manager = SynchronizeManager()
            instructions = (
                f"User info: {self.user.first_name} {self.user.last_name}, email: {self.user.email}\n"
                f"You are an academic presenter named Robowise, an expert English language teacher for beginners.\n"
                f"Follow this teaching methodology and roadmap:\n{TEACHING_PLAN}\n"
                f"Start the class with a warm greeting in English using the student's first name ({self.user.first_name}). "
                f"Introduce yourself and explain your methodology briefly in simple English (use clear and slow speech).\n"
                f"- Do NOT start teaching English concepts yet.\n"
                f"- Focus only on creating motivation, building comfort, and explaining how the sessions will work.\n"
                f"- Keep it short, friendly, and encouraging."
            )
            result = await self._run_blocking(sync_manager.full_synchronization_pipeline, instructions)
            await self._add_message_to_chat_history(result["ssml"], "ai_bot")
            return await self._send_json({
                "speech": result["audio_base64"],
                "slide_alignment": result["slide_alignment"],
                "remove_loader": True,
            })
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in starting the class: {str(e)}")

    # --------------------------------------------
    # Audio handler
    # --------------------------------------------
    async def _audio_handler(self, data):
        try:
            is_last_chunk = bool(data.get("is_last_chunk", False))
            audio_bytes = base64.b64decode(data.get("voice_chunk", ""))
            self.user_message += await self._run_blocking(
                self.audio_manager.convert_audio_to_text, audio_bytes=audio_bytes, do_final_edition=True, target_language="en"
            )
            if is_last_chunk:
                return await self._respond_to_user()
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in audio handler: {str(e)}")

    # --------------------------------------------
    # Respond to user
    # --------------------------------------------
    async def _respond_to_user(self):
        try:
            cur_message = self.user_message.strip()
            self.user_message = ""
            if len(cur_message) > 5000:
                cur_message = await self._run_blocking(
                    self.openai_manager.summarize,
                    text=cur_message,
                    max_length=5000,
                    max_chunk_size=1000,
                )
            messages_history = await self._add_message_to_chat_history(
                cur_message, self.user.first_name or "user"
            )
            sync_manager = SynchronizeManager()
            instructions = (
                f"Chat history:\n{messages_history}\n"
                f"\nInstructions:\n"
                f"{TEACHING_PLAN}\n"
                f"- Respond clearly if the question is related to English language learning.\n"
                f"- If the question is not related to English, politely say: 'In this class, we only focus on learning English.'\n"
                f"- If there are no new questions, continue teaching the NEXT English concept from the roadmap.\n"
                f"- Always teach in a complete, cohesive, and engaging way.\n"
                f"- Mix in pronunciation practice (ask the learner to repeat words or sentences).\n"
                f"- Use simple English with supportive explanations, but increase complexity gradually.\n"
                f"- After finishing a concept, check if the learner has any questions before moving on.\n"
                f"- Never repeat a concept once it has been taught, unless the learner explicitly asks for revision.\n"
                f"- Always progress to the next roadmap item when teaching autonomously.\n"
                f"- End each teaching segment with a short exercise or question (e.g., 'Can you try making a sentence with this word?').\n"
                f"- Do not greet or introduce yourself again once the class has started.\n"
                f"- If you gave the learner an exercise or practice in the last turn, WAIT for their response.\n"
                f"- Do not praise or continue until the learner actually tries or says something.\n"
                f"- If the learner is silent or did not respond, politely encourage them again instead of moving forward.\n"
            )
            result = await self._run_blocking(sync_manager.full_synchronization_pipeline, instructions, cur_message)
            await self._add_message_to_chat_history(result["ssml"], "ai_bot")
            return await self._send_json({
                "speech": result["audio_base64"],
                "slide_alignment": result["slide_alignment"],
                "remove_loader": True,
                "ssml": result["ssml"],
            })
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in responding to user: {str(e)}")
