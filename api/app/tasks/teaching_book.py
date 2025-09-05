from django.conf import settings

from core.models import UserModel
from ai.utils.open_ai_manager import OpenAIManager
from app.models import BookChatMessageModel, BookForUserModel

def add_message_to_chat_history(user_id, book_for_user_id, message, sender):
    user = UserModel.objects.filter(id=user_id).first()
    if not user:
        return
    book_for_user = BookForUserModel.objects.filter(id=book_for_user_id, user=user).first()
    if not book_for_user:
        return
    open_ai_manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY, cur_user=user)
    materials = open_ai_manager.build_materials_for_rag(message)
    for material in materials:
        BookChatMessageModel.objects.create(
            book_for_user=book_for_user,
            message=material["html"],
            message_embedding=material["vector"],
            sender=sender
        )
    