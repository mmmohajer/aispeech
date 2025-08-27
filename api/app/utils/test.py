from core.models import UserModel
from app.utils.book_data_manager import BookDataManager

def make_teaching_data_ready_for_user():
    cur_user = UserModel.objects.filter(email='mohammad@iswad.tech').first()
    if cur_user:
        with open("//websocket_tmp/texts/The Data Science Handbook.pdf", "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
        book_data_manager = BookDataManager(
            pdf_bytes=pdf_bytes,
            user_to_learn=cur_user,
            book_title="Book Title",
            target_language="en",
        )
        book_data_manager.learn_book()