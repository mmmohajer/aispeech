import asyncio
from django.core.cache import cache
from django.conf import settings
from django.db.models import F
from pgvector.django import CosineDistance
import json
import base64
import traceback
from google.cloud import texttospeech
from asgiref.sync import sync_to_async

from core.utils.redis_queue import RedisQueue
from ai.utils.open_ai_manager import OpenAIManager
from ai.utils.google_ai_manager import GoogleAIManager
from ai.utils.audio_manager import AudioManager
from ai.utils.synchronize_manager import SynchronizeManager
from websocket.consumers.base import BasePrivateConsumer, BasePrivateRoomBasedConsumer

TEACHING_TASKS = [
  {
    "id": 1,
    "title": "Hello, Document",
    "objective": "Introduce the skeleton of every HTML5 page.",
    "prompt": "Teach the student how to set up a valid HTML5 document. Explain <!DOCTYPE html>, <html lang>, <head> with title and meta charset, and <body>. Clarify why each is needed. End by asking the student to create a minimal HTML page with their own page title."
  },
  {
    "id": 2,
    "title": "Headings & Paragraphs",
    "objective": "Structure text meaningfully.",
    "prompt": "Explain headings (h1–h6) and paragraphs (p). Show how they create a logical document outline. Emphasize that only one h1 should exist per page. End with a small exercise: write a blog article title with subheadings and a few paragraphs."
  },
  {
    "id": 3,
    "title": "Emphasis & Inline Semantics",
    "objective": "Show that HTML conveys meaning, not just looks.",
    "prompt": "Teach inline semantic tags: em, strong, code, abbr, time, and q. Explain when to use them instead of visual-only formatting. Demonstrate with sentences like 'This is *important*' vs 'This is **critical**'. Ask the student to mark up a short paragraph with at least three of these tags."
  },
  {
    "id": 4,
    "title": "Lists & Navigation",
    "objective": "Introduce lists and the basis of navigation menus.",
    "prompt": "Explain ul, ol, and li. Show how nesting creates sublists. Teach how a nav element can contain a menu built with lists and links. Give an exercise: create a table of contents with three main items and one sublist, and a navigation bar with three links."
  },
  {
    "id": 5,
    "title": "Links & URLs",
    "objective": "Master linking inside and outside the page.",
    "prompt": "Explain the a element, href, absolute vs relative URLs, and internal anchors (#id). Demonstrate safe use of target=\"_blank\" with rel=\"noopener noreferrer\". Ask the student to build a list of three links: one internal anchor, one external site, and one email link (mailto:)."
  },
  {
    "id": 6,
    "title": "Images & Alternative Text",
    "objective": "Show how to embed images accessibly.",
    "prompt": "Teach the img tag, src, and alt. Explain accessibility: how screen readers use alt. Introduce figure and figcaption for describing images. Ask the student to add three images: one decorative, one informative, and one with a caption."
  },
  {
    "id": 7,
    "title": "Tables for Data",
    "objective": "Teach semantic data tables.",
    "prompt": "Explain how to create a table with table, caption, thead, tbody, tfoot, tr, th, and td. Show how scope makes headers accessible. Demonstrate with a gradebook or price list. Ask the student to create a 3x3 table with column headers and a caption."
  },
  {
    "id": 8,
    "title": "Semantic Layout",
    "objective": "Introduce modern landmark tags.",
    "prompt": "Teach semantic layout elements: header, main, section, article, aside, and footer. Show how they improve accessibility and document structure. Ask the student to create a simple news article page using these elements."
  },
  {
    "id": 9,
    "title": "Forms I — Basics",
    "objective": "Teach simple user input collection.",
    "prompt": "Explain the basics of forms: form, label, input type=\"text\", input type=\"email\", textarea, and button. Show how label for connects to inputs. Ask the student to build a contact form with name, email, and message."
  },
  {
    "id": 10,
    "title": "Forms II — Choices",
    "objective": "Teach checkboxes, radios, and dropdowns.",
    "prompt": "Explain radio buttons (exclusive choice), checkboxes (multiple choice), and selects with options. Demonstrate with a pizza order form (size: small/medium/large as radio buttons; toppings as checkboxes; delivery method as select dropdown). Ask the student to replicate."
  },
  {
    "id": 11,
    "title": "Forms III — Accessibility & Validation",
    "objective": "Teach user guidance and constraints.",
    "prompt": "Show how to use fieldset + legend, placeholders, required, pattern, and aria-describedby. Teach how browsers give feedback for validation. Ask the student to improve their contact form by adding required fields and a validation pattern for phone number."
  },
  {
    "id": 12,
    "title": "Multimedia",
    "objective": "Introduce embedding audio and video.",
    "prompt": "Teach the <audio> and <video> tags with the controls attribute. Explain <source> for multiple formats and <track> for captions. Ask the student to embed one audio file and one video file with captions."
  },
  {
    "id": 13,
    "title": "Metadata, SEO & Social",
    "objective": "Teach head metadata for search engines & social.",
    "prompt": "Explain the role of <meta> description, viewport, and Open Graph tags (title, description, image). Show how link previews use this. Ask the student to add a meta description and viewport tag to their HTML page."
  },
  {
    "id": 14,
    "title": "Accessibility Pass",
    "objective": "Build inclusive habits.",
    "prompt": "Review accessibility essentials: lang on <html>, heading order, descriptive link text, keyboard navigation. Ask the student to inspect one of their previous pages and fix accessibility issues (e.g., change 'click here' to meaningful link text)."
  },
  {
    "id": 15,
    "title": "Capstone Mini-Site",
    "objective": "Put it all together.",
    "prompt": "Ask the student to build a 3–5 page micro-site (Home, About, Contact, Articles). Require: Semantic layout with header/nav/main/footer, at least one table, one accessible form, proper meta description and Open Graph tags. Evaluate by checking structure, accessibility, and validity."
  }
]

class TeacherConsumer(BasePrivateRoomBasedConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_manager = None
        self.google_manager = None
        self.audio_manager = None
        self.user_message = ""
        self.chat_history = []

    async def connect(self):
        await super().connect()
        if self.profile.user:
            self.openai_manager = OpenAIManager(
                model="gpt-4o",
                api_key=settings.OPEN_AI_SECRET_KEY,
                cur_user=self.profile.user,
            )
            self.google_manager = GoogleAIManager(
                api_key=settings.GOOGLE_API_KEY,
                cur_user=self.profile.user
            )
            self.audio_manager = AudioManager()
            self.tasks = RedisQueue(name=f"class_room_{self.room_id}_tasks", timeout=3600)
            cache.set(f"class_room_{self.room_id}_is_active", True, timeout=3600)
            asyncio.create_task(self._task_runner())

    async def _task_runner(self):
        while cache.get(f"class_room_{self.room_id}_is_active", False):
            task = self.tasks.get_task()
            if task:
                await self._run_task(task)
            else:
                await asyncio.sleep(1)
    
    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                data = json.loads(text_data)
                task = data.get("task") or ""
                if task == "start_the_class":
                    cache_key = f"class_room_{self.room_id}_class_started"
                    class_started = cache.get(cache_key, False)
                    if not class_started:
                        cache.set(cache_key, True, None)
                        self.tasks.add_priority_task({"task": "start_the_class", "metadata": None})
                        for task in TEACHING_TASKS:
                            self.tasks.add_task({
                                "task": "teach_new_content",
                                "metadata": dict(task)
                            })
                elif task == "listen_to_audio":
                    self.tasks.add_priority_task({"task": "listen_to_audio", "metadata": data})
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in receiving data: {str(e)}")

    async def _run_task(self, task):
        task_type = task.get("task")
        if task_type == "start_the_class":
            await self._start_the_class()
        elif task_type == "teach_new_content":
            self._techch_new_content(task.get("metadata"))
        elif task_type == "listen_to_audio":
            await self._audio_handler(task.get("metadata"))
        else:
            await self._send_json({"error": f"Unknown task {task_type}"})
    
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
                f"User info: {self.profile.user.first_name} {self.profile.user.last_name}, email: {self.profile.user.email}\n"
                f"You are an academic presenter named Angelica, an expert in HTML, teaching early junior developers.\n"
                f"Start the class with a warm greeting using the user's first name ({self.profile.user.first_name}). "
                f"Introduce yourself and briefly explain your teaching methodology (slides, examples, quizzes, exercises, projects). "
                f"Then clearly outline the materials that will be covered in this course:\n{TEACHING_TASKS}\n"
                f"Important: Do NOT begin teaching any HTML concepts yet — only greet, introduce methodology, and present the roadmap."
            )
            result = await self._run_blocking(sync_manager.full_synchronization_pipeline, instructions)
            await self._add_message_to_chat_history(result["ssml"], "ai_bot")
            return await self._send_to_group({
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
                cur_message, self.profile.user.first_name or "user"
            )
            sync_manager = SynchronizeManager()
            instructions = (
                f"You are an HTML teacher named Angelica. "
                f"Here is the teaching plan you are following:\n{TEACHING_TASKS}\n\n"
                f"Here is the chat history (what the user has already learned and asked):\n{messages_history}\n\n"
                f"The user just said:\n\"{cur_message}\"\n\n"
                f"Your only priority is to generate a direct and natural response to the user’s message. "
                f"- If it’s a question related to HTML, give a clear, complete answer with examples. "
                f"- If it’s unrelated, politely redirect: 'In this class, we only teach about HTML.' "
                f"- If it’s not a question but more of an acknowledgment (like 'ok', 'sounds good', etc.), reply positively in a friendly way (e.g., 'Great! That sounds good.'). "
                f"Do not continue teaching HTML concepts in this step — just respond to the user’s message."
            )
            result = await self._run_blocking(sync_manager.full_synchronization_pipeline, instructions, cur_message)
            await self._add_message_to_chat_history(result["ssml"], "ai_bot")
            return await self._send_to_group({
                "speech": result["audio_base64"],
                "slide_alignment": result["slide_alignment"],
                "remove_loader": True,
                "ssml": result["ssml"],
            })
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in responding to user: {str(e)}")
    
    # --------------------------------------------
    # Teach new content
    # --------------------------------------------
    async def _teach_new_content(self, data):
        try:
            sync_manager = SynchronizeManager()

            instructions = (
                f"You are an academic presenter named Angelica, an expert in HTML, teaching early junior developers.\n"
                f"This is the next lesson you must teach from the course materials.\n\n"
                f"Lesson ID: {data.get('id')}\n"
                f"Title: {data.get('title')}\n"
                f"Objective: {data.get('objective')}\n"
                f"Teaching Instructions: {data.get('prompt')}\n\n"
                f"Teach this content clearly, step by step, with simple examples and engaging explanations. "
                f"Do not jump to other lessons. Stay focused only on this lesson."
            )

            result = await self._run_blocking(
                sync_manager.full_synchronization_pipeline,
                instructions
            )

            await self._add_message_to_chat_history(result["ssml"], "ai_bot")

            return await self._send_to_group({
                "speech": result["audio_base64"],
                "slide_alignment": result.get("slide_alignment"),
                "remove_loader": True,
                "ssml": result["ssml"],
                "task_id": data.get("id"),
                "task_title": data.get("title")
            })
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in teaching new content: {str(e)}")