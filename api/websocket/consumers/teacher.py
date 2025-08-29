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
from app.models import (
    BookForUserModel,
    BookChunkModel,
    BookTeachingContentModel,
    BookChatMessageModel,
)
from websocket.consumers.base import BasePrivateConsumer


class TeacherConsumer(BasePrivateConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_manager = None
        self.google_manager = None
        self.audio_manager = None
        self.user_message = ""
        self.chat_messages = []
        self.chat_history = []
        self.book_for_user = None
        self.content_to_teach = None
        self.q_a_list = []

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
                cur_user=self.user,
            )
            self.audio_manager = AudioManager()
            self.book_for_user = await sync_to_async(
                lambda: BookForUserModel.objects.filter(user__email=self.user.email).first()
            )()
            if not self.book_for_user:
                return await self._handle_error("No book found for the user.")

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
    # Get next concept to teach
    # --------------------------------------------
    async def _get_next_content_to_teach(self):
        next_concept = await sync_to_async(
            lambda: BookTeachingContentModel.objects.filter(
                book_for_user=self.book_for_user, user_has_learned=False
            )
            .exclude(content__isnull=True)
            .exclude(content="")
            .exclude(q_and_a__isnull=True)
            .exclude(q_and_a=[])
            .extra(where=["LENGTH(content) >= 50"])
            .order_by("chunk_index")
            .first()
        )()
        if not next_concept:
            self.content_to_teach = None
            self.q_a_list = []
            return

        # Mark concept as learned
        await sync_to_async(
            lambda: BookTeachingContentModel.objects.filter(
                id=next_concept.id
            ).update(user_has_learned=True),
            thread_sensitive=True,
        )()

        # Get Q&A for this exact chunk index
        q_and_a_list = await sync_to_async(
            lambda: list(
                BookTeachingContentModel.objects.filter(
                    book_for_user=self.book_for_user,
                    chunk_index=next_concept.chunk_index,
                ).values_list("q_and_a", flat=True)
            )
        )()
        self.q_a_list = [
            item for sublist in q_and_a_list for item in (sublist if isinstance(sublist, list) else [sublist])
        ]

        self.content_to_teach = next_concept.content

    # --------------------------------------------
    # Start the class
    # --------------------------------------------
    async def _start_the_class(self):
        try:
            book_summary = self.book_for_user.summary

            chat_messages = await sync_to_async(
                lambda: list(
                    BookChatMessageModel.objects.filter(
                        book_for_user=self.book_for_user
                    ).order_by("created_at")
                )
            )()
            chat_texts = [msg.message for msg in chat_messages]
            chat_summary = await self._run_blocking(
                self.openai_manager.summarize,
                "\n".join(chat_texts[-20:]) if chat_texts else "No previous chats.",
            )

            is_first_session = len(chat_messages) == 0
            await self._get_next_content_to_teach()

            sync_manager = SynchronizeManager()
            instructions = (
                f"Book summary: {book_summary}\n"
                f"User info: {self.user.first_name} {self.user.last_name}, email: {self.user.email}\n"
                f"{(
                    'Introduce yourself warmly, explain your expertise, and express excitement to teach this book. '
                    'Start with a friendly greeting, address the user by their name, give a concise summary of the book, '
                    'explain how sessions will work, and then smoothly transition into today\'s first concept: '
                    f"{self.content_to_teach or 'No content available.'}"
                ) if is_first_session else (
                    'Greet the user by their name for today\'s session. '
                    'Give a very brief recap of previous session(s) using this summary: '
                    f"{chat_summary}. "
                    'Use a connector phrase to shift naturally into the next concept, for example: '
                    "'Now that we’ve reviewed what we covered last time, let’s continue with today’s topic: "
                    f"{self.content_to_teach or 'No content available.'}'."
                )}\n\n"

                "Classroom Management:\n"
                "- Always act like a real teacher in a live class (warm, structured, adaptive).\n"
                "- Alternate naturally between teaching and short comprehension checks, but never interrupt the flow of an explanation.\n"
                "- Do NOT insert comprehension questions in the middle of an explanation. Place only one engagement or comprehension check at the end of each explanation block.\n"
                "- Use connector phrases to make transitions smooth. Examples:\n"
                "   • 'Great, now that we’ve covered that, let’s dive into...'\n"
                "   • 'Perfect, that clears it up. Next, we’ll look at...'\n"
                "   • 'Alright, since that’s answered, let’s continue with...'\n"
                "- If the user's message is unclear, silent, or too short, politely ask them to repeat, speak louder, or clarify.\n"
                "- If the user gives a short valid answer (e.g., 'ok', 'thanks'), acknowledge warmly, then either check their understanding or transition smoothly.\n"
                "- If the user asks a question:\n"
                "   * If relevant, answer thoroughly using the book.\n"
                "   * After answering, use a connector phrase before resuming the lesson.\n"
                "   * If irrelevant, politely redirect back to the topic.\n"
                "- Don’t ask more than 3 comprehension questions in a row without teaching in between.\n"
                "- Use the Q&A list as a source of questions, but rephrase naturally so it doesn’t sound robotic.\n"
                "- Mix engagement styles: end-of-block questions, quick recaps, relatable examples.\n"
                "- Always close each response by engaging the student: ask if they have questions, confirm understanding, or invite them to continue with the next concept.\n"
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
            await self._send_json({"user_message": self.user_message})
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
            await self._get_next_content_to_teach()
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

            processed_cur_message = await self._run_blocking(
                self.openai_manager.build_materials_for_rag,
                text=cur_message,
                max_chunk_size=5000,
            )
            cur_message_embedding = processed_cur_message[0]["vector"]

            threshold = 0.3
            similar_chunks = await sync_to_async(
                lambda: list(
                    BookChunkModel.objects.filter(book_for_user__user__email=self.user.email)
                    .annotate(distance=CosineDistance("embedding", cur_message_embedding))
                    .filter(distance__lte=threshold)
                    .order_by("distance")[:5]
                )
            )()

            chunk_indices = [chunk.chunk_index for chunk in similar_chunks]
            neighbor_indices = {idx - 1 for idx in chunk_indices if idx > 0} | {idx + 1 for idx in chunk_indices}
            all_indices = set(chunk_indices) | neighbor_indices

            all_chunks = await sync_to_async(
                lambda: list(
                    BookChunkModel.objects.filter(
                        book_for_user__user__email=self.user.email, chunk_index__in=all_indices
                    ).order_by("chunk_index")
                )
            )()
            response_from_book = "\n\n".join(chunk.chunk_text for chunk in all_chunks)

            sync_manager = SynchronizeManager()
            
            instructions = (
                f"Current concept: {self.content_to_teach}\n"
                f"Chat history:\n{messages_history}\n"
                f"Relevant book content:\n{response_from_book}\n"
                f"Q&A for the last taught concept: {self.q_a_list}\n\n"

                "Response Priorities:\n"
                "1. Always respond to the user's most recent input first.\n"
                "2. Use chat history to maintain continuity with the current lesson.\n"
                "3. Use relevant book content to support and enrich explanations.\n"
                "4. Introduce the 'Current concept' only when it is the right moment to transition — "
                "never jump ahead unless the user shows readiness or the previous concept is wrapped up.\n\n"

                "Classroom Management:\n"
                "- Always act like a real teacher in a live class (warm, structured, adaptive).\n"
                "- Alternate naturally between teaching, short comprehension checks, and engagement.\n"
                "- Do NOT insert comprehension questions in the middle of an explanation. "
                "Only place ONE engagement or comprehension check at the end of the explanation block.\n"
                "- If the user's message is unclear, silent, or too short, politely ask them to repeat, "
                "speak louder, or clarify.\n"
                "- If the user gives a short valid answer (e.g., 'ok', 'thanks'), acknowledge warmly, "
                "then either check their understanding or continue smoothly.\n"
                "- If the user asks a question:\n"
                "   * If relevant, answer thoroughly using the book.\n"
                "   * After answering, use connector phrases to resume teaching smoothly.\n"
                "   * If irrelevant, politely redirect back to the topic.\n"
                "- Don’t ask more than 3 comprehension questions in a row without teaching in between.\n"
                "- Use the Q&A list as a source of questions, but vary phrasing so it sounds natural.\n"
                "- Mix engagement styles: end-of-block questions, brief recaps, relatable examples, or quick reviews.\n"
                "- Use connector phrases to transition into new concepts. Examples:\n"
                "   • 'Now that we’ve covered X, let’s dive into Y.'\n"
                "   • 'Alright, since your question is answered, let’s continue with...'\n"
                "   • 'Perfect, that clears it up. Next, let’s look at...'\n"
                "- Always close each response by engaging the student: ask if they have questions, "
                "confirm understanding, or invite them to continue to the next concept.\n"
            )

            result = await self._run_blocking(sync_manager.full_synchronization_pipeline, instructions, cur_message)
            await self._add_message_to_chat_history(result["ssml"], "ai_bot")
            with open(f"/websocket_tmp/ai/last_ssml_{self.user.id}.json", "w") as f:
                json.dump({
                    "slide_alignment": result["slide_alignment"],
                    "ssml": result["ssml"],
                    "audio_length_sec": result["audio_length_sec"],
                    "timepoints": result["timepoints"],
                    "remove_loader": True,
                    "instructions": instructions,
                }, f, ensure_ascii=False, indent=2)
            return await self._send_json({
                "speech": result["audio_base64"],
                "slide_alignment": result["slide_alignment"],
                "ssml": result["ssml"],
                "audio_length_sec": result["audio_length_sec"],
                "timepoints": result["timepoints"],
                "remove_loader": True,
                "instructions": instructions,
            })
        except Exception as e:
            traceback.print_exc()
            return await self._handle_error(f"Error in responding to user: {str(e)}")
