from django.conf import settings

from core.models import ProfileModel, UserModel
from ai.utils.ocr_manager import OCRManager
from ai.utils.open_ai_manager import OpenAIManager
from app.models import BookForUserModel, BookChunkModel, BookTeachingContentModel


class BookDataManager:
    def __init__(self, pdf_bytes, user_to_learn, book_title, target_language="en", start_page=None, end_page=None):
        self.pdf_bytes = pdf_bytes
        self.user_to_learn = user_to_learn
        self.book_title = book_title
        self.target_language = target_language
        self.ocr_manager = OCRManager(
            google_cloud_project_id=settings.GOOGLE_CLOUD_DOCUMENT_AI_PROJECT_ID,
            google_cloud_location=settings.GOOGLE_CLOUD_DOCUMENT_AI_LOCATION,
            google_cloud_processor_id=settings.GOOGLE_CLOUD_DOCUMENT_AI_PROCESSOR_ID,
            cur_user=self.self.user_to_learn
        )
        self.open_ai_manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY, cur_user=self.user_to_learn)
        self.start_page = start_page
        self.end_page = end_page

    def _ocr_progress_callback(self, page, total):
        percent = int((page / total) * 100)
        print(f"Processing page {page}/{total} ({percent}%)")

    def _rag_progress_callback(self, chunk=None, index=None, total=None, err_msg=None):
        if err_msg:
            print(f"[ERROR] Chunk {index}/{total}: {err_msg}")
        elif chunk is not None:
            percent = int((index / total) * 100)
            print(f"Processing chunk {index}/{total} ({percent}%)")
    
    def _summarize_progress_callback(self, chunk, index, total):
        percent = int((index / total) * 100)
        print(f"Summarizing chunk {index}/{total} ({percent}%)")
    
    def _teaching_progress_callback(self, chunk, index, total):
            percent = int((index / total) * 100)
            print(f"Teaching content chunk {index}/{total} ({percent}%)")

    
    def learn_book(self):
        self.ocr_manager.clear_cost()
        self.open_ai_manager.clear_cost()
        html_src, text = self.ocr_manager.read_pdf_bytes(self.pdf_bytes, progress_callback=self._ocr_progress_callback, start_page=self.start_page, end_page=self.end_page)
        summary = self.open_ai_manager.summarize(text=text, max_length=2000, max_chunk_size=15000, progress_callback=self._summarize_progress_callback)
        cur_book_for_user = BookForUserModel()
        cur_book_for_user.user = self.user_to_learn
        cur_book_for_user.title = self.book_title
        cur_book_for_user.summary = summary
        cur_book_for_user.save()
        materials = self.open_ai_manager.build_materials_for_rag(text=html_src, progress_callback=self._rag_progress_callback)
        for material in materials:
            BookChunkModel.objects.create(
                book_for_user=cur_book_for_user,
                chunk_index=material['chunk_number'],
                chunk_text=material['text'],
                chunk_html=material['html'],
                embedding=material['vector']
            )

        all_teaching_content = self.open_ai_manager.build_teaching_content_for_a_text(
            text=html_src,
            target_language=self.target_language,
            max_chunk_size=5000,
            max_teaching_tokens=5000,
            progress_callback=self._teaching_progress_callback)
        for idx, chunk_content in enumerate(all_teaching_content):
            BookTeachingContentModel.objects.create(
                book_for_user=cur_book_for_user,
                chunk_index=idx,
                content=chunk_content.get("clarifying_concept_to_teach", ""),
                q_and_a=chunk_content.get("q_and_a_list", []),
                user_has_learned=False
            )