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
Teaching Plan for HTML Course:

1. Introduction & Methodology
- Warm welcome using user’s first name.
- Explain flow: slides, real-world examples, quizzes, exercises, projects.
- Encourage questions; adapt pace.

2. Course Roadmap
- HTML Foundations: document structure, headings, paragraphs, comments.
- Text & Content Formatting: bold, italics, lists, links.
- Multimedia: images, audio, video, iframes.
- Forms & User Input: inputs, labels, checkboxes, dropdowns, buttons.
- Layout & Structure: divs, spans, semantic elements, tables.
- Advanced Topics: meta tags, favicons, accessibility, clean code practices.

3. Teaching Style per Session
- Start with slides and explanations.
- Use analogies and real-world examples.
- Quick quizzes to reinforce concepts.
- Practical exercise after each lesson.
- Mini-project after major milestone.

4. Engagement Rules
- Answer HTML questions in depth.
- Politely redirect if off-topic.
- Use progressive complexity: start simple → build up.

5. Session Wrap-Up
- Provide notes and quiz.
- Assign challenge.
- Hint at next session.
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
                f"You are an academic presenter named Angelica, an expert in HTML, teaching early junior developers.\n"
                f"Follow this teaching methodology and roadmap:\n{TEACHING_PLAN}\n"
                f"Start the class with a warm greeting using the user's first name ({self.user.first_name}). "
                f"Introduce yourself and explain your methodology briefly. "
                f"Do NOT teach any HTML concept in this introduction."
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
                f"- Respond clearly if the question is related to HTML.\n"
                f"- If the question is not related, politely say: 'In this class, we only teach about HTML.'\n"
                f"- If there are no new questions, continue teaching the next HTML concept from the roadmap.\n"
                f"- Always teach in a complete, cohesive, and engaging way.\n"
                f"- After finishing a concept, check for questions before moving on.\n"
                f"- Never repeat a concept once it has been taught, unless the user explicitly asks for revision.\n"
                f"- Always progress to the next roadmap item when teaching autonomously.\n"

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
