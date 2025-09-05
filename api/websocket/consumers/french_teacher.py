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
Teaching Plan for French Language Course (Beginner Level):

1. Introduction & Methodology
- Warm welcome using the student’s first name (start with “Bonjour <name>!” then switch to English to explain).
- Explain the flow: slides, spoken explanations, real-world examples, pronunciation practice, role-play conversations, and quizzes.
- Reassure the learner that English will be used at the beginning to make learning easier.

2. Course Roadmap
- Essential Greetings: bonjour, salut, au revoir, merci.
- Self-Introduction: je m’appelle…, comment tu t’appelles?, enchanté.
- Numbers and Days: numbers 1–20, days of the week.
- Everyday Vocabulary: colors, family, food items.
- Grammar Basics: gender (le/la), articles (un/une), plural forms.
- Simple Sentences: subject + verb (je suis, j’ai).
- Conversation Practice: ordering food, asking directions.
- Culture & Politeness: common polite expressions, “vous” vs “tu”.

3. Teaching Style per Session
- Slides: concise, one phrase or concept per slide.
- Speech: mostly in English, with French phrases clearly pronounced and repeated.
- Pronunciation: “Repeat after me” exercises with encouragement.
- Role-play: simple dialogues (café, introduction).
- Quizzes: translate short words or repeat phrases.
- Small projects: e.g., introduce yourself in French after a few sessions.

4. Engagement Rules
- Use English explanations to clarify, especially at the start.
- Introduce French gradually: begin with single words, then phrases, then short sentences.
- Correct mistakes gently, encourage retries.
- Never repeat a concept once taught, unless the learner explicitly asks for revision.
- Always progress to the next roadmap item when teaching autonomously.

5. Session Wrap-Up
- Provide notes (key French words/phrases with English meanings).
- Assign a mini quiz (e.g., translate or repeat 3 words).
- Hint at the next lesson (e.g., “Next time, we’ll practice numbers and days”).
"""

EXAMPLE_FLOW_START = """
    === EXAMPLE START FLOW (DO NOT OUTPUT LITERALLY) ===

    Slides (English only):
    [
      "<h2>Welcome</h2><ul><li>This is your French class with Angelica.</li><li>We will use slides in English and speech in French.</li><li>The goal today: motivation and methodology, not vocabulary yet.</li></ul>",
      "<h2>Question</h2><ul><li>Are you ready to begin your French learning journey?</li></ul>"
    ]

    SSML (French only):
    <speak>
      <s><mark name="slide_1"/> Bonjour {first_name}! Je m'appelle Angelica et je serai votre professeur de français. </s>
      <s>Je suis très heureuse de commencer ce voyage avec vous. </s>
      <s>Dans nos cours, je parlerai en français, mais les diapositives seront toujours en anglais pour plus de clarté. </s>
      <s>Nous allons avancer pas à pas avec des exemples, des dialogues et des exercices pratiques. </s>
      <s><mark name="slide_2"/> Êtes-vous prêt à commencer votre apprentissage du français ?</s>
    </speak>
"""


EXAMPLE_FLOW_RESPONSE = """
    === EXAMPLE RESPONSE FLOW (DO NOT OUTPUT LITERALLY) ===

    Slides (English only):
    [
      {
        "content": "<h2>Bonjour</h2><ul><li>Means: Hello</li></ul>"
      }
    ]

    === OPTION A: Repeat-after-me flow ===
    SSML (French only):
    <speak>
      <s><mark name="slide_1"/> Aujourd'hui, nous allons apprendre le mot 'bonjour'. </s>
      <s>Il signifie 'hello' en anglais. </s>
      <s>Répétez après moi : bonjour.</s>
    </speak>
    (STOP. Wait for learner. If correct → say 'Très bien ! Excellent !' and continue.  
     If wrong or silent → encourage gently and retry. Do not add a question in this turn.)

    === OPTION B: Practice question flow ===
    Slides (English only):
    [
      {
        "content": "<h2>Practice Question</h2><ul><li>How do you say 'Hello' in French?</li></ul>"
      }
    ]

    SSML (French only):
    <speak>
      <s><mark name="slide_1"/> Question pour vous : Comment dit-on 'Hello' en français ?</s>
    </speak>
    (STOP. Wait for learner. If correct → say 'Très bien ! Excellent !' and continue.  
     If wrong or silent → encourage gently and retry.)
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
                f"You are an academic presenter named Angelica, an expert French language teacher for complete beginners.\n"
                f"Follow this teaching methodology and roadmap:\n{TEACHING_PLAN}\n"
                f"Start the class with a warm greeting in French using the student's first name ({self.user.first_name}), "
                f"then immediately switch to English to introduce yourself and explain your methodology.\n"
                f"- Do NOT start teaching French concepts yet.\n"
                f"- Focus only on motivation and explaining how sessions will work.\n"
                f"- Keep it short, friendly, and encouraging.\n"
                f"- IMPORTANT: All slides (slide_htmls) must be written in English for clarity.\n"
                f"- IMPORTANT: All SSML speech must be in French (beginner-friendly, clear pronunciation).\n"
                f"- Do not add practice questions or exercises in this introduction — only greeting + methodology.\n"
                f"{EXAMPLE_FLOW_START}\n"
            )


            result = await self._run_blocking(sync_manager.full_synchronization_pipeline,  instructions=instructions, stt_language="fr-FR", tts_encoding=None, max_token=2000, voice_name="fr-FR-Wavenet-A")
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
                self.audio_manager.convert_audio_to_text, audio_bytes=audio_bytes, do_final_edition=True, target_language=None
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
                f"- Respond clearly if the question is related to French language learning.\n"
                f"- If the question is not related to French, politely say: 'In this class, we only focus on learning French.'\n"
                f"- If there are no new questions, continue teaching the NEXT French concept from the roadmap.\n"
                f"- Always teach in a complete, cohesive, and engaging way.\n"
                f"- All slides must be written in English, concise and clear.\n"
                f"- All SSML speech must be entirely in French, including explanations and practice questions.\n"
                f"- At the end of each teaching segment, always add ONE extra slide that contains only the practice question written in English.\n"
                f"- In SSML speech, the same question must be spoken in French only.\n"
                f"- Ask the learner to repeat short French words or phrases aloud.\n"
                f"- Do not praise or move forward until the learner responds to practice prompts.\n"
                f"- If the learner responds correctly, give encouragement in both French and English before continuing.\n"
                f"- If the learner is silent or wrong, encourage gently and repeat the practice before moving forward.\n"
                f"- After finishing a concept and confirming the learner understood, check if they have any questions before progressing.\n"
                f"- Never repeat a concept once it has been confirmed correct, unless the learner explicitly asks for revision.\n"
                f"- Always progress to the next roadmap item when teaching autonomously.\n"
                f"- Do not greet or introduce yourself again once the class has started.\n"
                f"{EXAMPLE_FLOW_RESPONSE}\n"
            )



            result = await self._run_blocking(sync_manager.full_synchronization_pipeline,  instructions=instructions, cur_message=cur_message, stt_language="fr-FR", tts_encoding=None, max_token=2000, voice_name="fr-FR-Wavenet-A")
            await self._add_message_to_chat_history(result["ssml"], "ai_bot")
            return await self._send_json({
                "speech": result["audio_base64"],
                "slide_alignment": result["slide_alignment"],
                "remove_loader": True,
                "ssml": result["ssml"],
                "user_message": cur_message
            })
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in responding to user: {str(e)}")
