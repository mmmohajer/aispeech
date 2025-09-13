from pydub import AudioSegment
import requests
import io
import os

from core.models import UserModel
from config.utils.storage_manager import CloudStorageManager
from app.models import ClassRoomModel, ClassRoomContentModel
from app.utils.book_data_manager import BookDataManager
from app.utils.class_room_manager import ClassRoomManager

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



def test_class_room_manager():
    
    class_room_manager = ClassRoomManager(
        instructions="You are an academic presenter named Angelica, an expert in HTML, teaching early junior developers.", teaching_tasks=TEACHING_TASKS
    )
    class_room = class_room_manager.build_a_room(
        title="HTML Basics",
        description="Learn the basics of HTML.",
        teacher_voice_name="en-US-Wavenet-F",
        language="en"
    )
    print(f"Created Class Room: {class_room}")

    member = class_room_manager.add_member_to_room(user_email="mohammad@iswad.tech")
    print(f"Added Member: {member}")

    members = class_room_manager.get_room_members()
    print(f"Room Members: {[str(m) for m in members]}")

    contents = class_room_manager.build_teaching_contents()
    print(f"Created Contents: {[str(c) for c in contents]}")

def merge_classroom_audios(classroom_uuid="f8cfb1d9-884c-413f-9a1a-d84a62a3f5c4", output_path="/websocket_tmp/merged_classroom/audio.wav"):
    classroom = ClassRoomModel.objects.get(uuid=classroom_uuid)
    contents = ClassRoomContentModel.objects.filter(class_room=classroom).order_by("order")
    merged_audio = None
    cloud_manager = CloudStorageManager()
    for content in contents:
        if not content.audio_file:
            continue
        file_url = cloud_manager.get_url(bucket="AI", file_key=content.audio_file, acl="private")
        resp = requests.get(file_url)
        resp.raise_for_status()
        audio = AudioSegment.from_file(io.BytesIO(resp.content), format="wav")
        if merged_audio is None:
            merged_audio = audio
        else:
            merged_audio += audio
    if merged_audio:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fmt = "wav" if output_path.endswith(".wav") else "mp3"
        merged_audio.export(output_path, format=fmt)
        return output_path

    return None

def test():
    merge_classroom_audios()