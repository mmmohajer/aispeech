from django.conf import settings
import json
import base64
from google.cloud import texttospeech
from asgiref.sync import sync_to_async


from ai.utils.open_ai_manager import OpenAIManager
from ai.utils.google_ai_manager import GoogleAIManager
from ai.utils.audio_manager import AudioManager
from app.models import BookForUserModel, BookChunkModel, BookTeachingContentModel, BookChatMessageModel
from websocket.consumers.base import BasePrivateConsumer

class TeacherConsumer(BasePrivateConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)
        self.google_manager = GoogleAIManager(api_key=settings.GOOGLE_API_KEY)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
               data = json.loads(text_data)
               task = data.get("task") if data.get("task") else ""
            if task == "start_the_class":
                await self._start_the_class()        
        except Exception as e:
            print(e)
        return
    
    # --------------------------------------------
    # --------------------------------------------
    # Beginning of Start The Class Task
    # --------------------------------------------
    # --------------------------------------------
    async def _start_the_class(self):
        print("Starting the class...")

        # -------------------------------
        # 1. Get book_for_user
        # -------------------------------
        book_for_user = await sync_to_async(
            lambda: BookForUserModel.objects.filter(user__email=self.user.email).first()
        )()
        if not book_for_user:
            return await self._handle_error("No book found for the user.")

        # -------------------------------
        # 2. Get book summary
        # -------------------------------
        print("Get book summary")
        book_summary = book_for_user.summary

        # -------------------------------
        # 3. Get chat history & summary
        # -------------------------------
        print("Get chat history summary")
        chat_messages = await sync_to_async(
            lambda: list(
                BookChatMessageModel.objects
                .filter(book_for_user=book_for_user)
                .order_by("created_at")
            )
        )()
        chat_texts = [msg.message for msg in chat_messages]
        chat_summary = await self._run_blocking(
            self.openai_manager.summarize,
            "\n".join(chat_texts[-20:]) if chat_texts else "No previous chats."
        )

        # -------------------------------
        # 4. Is this the first session?
        # -------------------------------
        print("Is this the first session?")
        is_first_session = len(chat_messages) == 0

        # -------------------------------
        # 5. Get next concept to teach
        # -------------------------------
        print("Get next concept to teach")
        next_concept = await sync_to_async(
            lambda: BookTeachingContentModel.objects
                .filter(
                    book_for_user=book_for_user,
                    user_has_learned=False
                )
                .exclude(content__isnull=True)
                .exclude(content="")
                .exclude(q_and_a__isnull=True)
                .exclude(q_and_a=[])
                .extra(where=["LENGTH(content) >= 50"])
                .order_by("chunk_index")
                .first()
        )()
        content_to_teach = next_concept.content if next_concept else None
        list_of_questions = next_concept.q_and_a if next_concept else []

        # -------------------------------
        # 6. Build system prompt
        # -------------------------------
        print("Build system prompt for OpenAI")
        if is_first_session:
            system_prompt = (
                f"You are a master teacher for a book.\n"
                f"Book summary: {book_summary}\n"
                f"Introduce yourself to the user, explain your expertise, and express your excitement to teach this book. "
                f"Start with a friendly greeting, then give a brief summary of the book, and explain how the sessions will work. "
                f"Today's first concept: {content_to_teach if content_to_teach else 'No content available.'}"
            )
        else:
            system_prompt = (
                f"You are a master teacher for a book.\n"
                f"Book summary: {book_summary}\n"
                f"Greet the user for today's session. "
                f"Give a quick review of the last session(s) using these chat summaries: {chat_summary}\n"
                f"Then, introduce the next concept to teach: {content_to_teach if content_to_teach else 'No content available.'}"
            )

        # -------------------------------
        # 7. Generate greeting
        # -------------------------------
        print("Add system prompt to OpenAIManager and generate response")
        self.openai_manager.add_message("system", system_prompt)
        response = await self._run_blocking(self.openai_manager.generate_response)

        # -------------------------------
        # 8. Send response to client
        # -------------------------------
        await self._send_json({
            "greeting": response,
            "first_session": is_first_session,
            "book_summary": book_summary,
            "next_concept": content_to_teach,
            "questions": list_of_questions,
            "chat_review": chat_summary
        })
    # --------------------------------------------
    # --------------------------------------------
    # End of Start The Class Task
    # --------------------------------------------
    # --------------------------------------------