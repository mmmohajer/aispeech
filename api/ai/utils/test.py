import base64
from pydoc import text
from django.conf import settings
import json
import os
from google.cloud import texttospeech, speech

from ai.utils.open_ai_manager import OpenAIManager
from ai.utils.google_ai_manager import GoogleAIManager
from ai.utils.ocr_manager import OCRManager

def test_get_response():
    manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)
    manager.add_message("system", text="You are a helpful assistant, that receives a text and will generate a json including user_message and a random id")
    manager.add_message("system", text="Format of the json is like {'user_message': <user_message>, 'id': <random_id>}")
    manager.add_message("user", text="Hello, world!")
    response = manager.generate_response()
    cost = manager.get_cost()
    json_response = json.loads(response)
    print(json_response['id'])
    print(f"Response: {json.dumps(json_response, indent=2)}")
    print(f"Cost: {cost}")

def test_convert_html_to_text():
    html_file_path = os.path.join(settings.MEDIA_ROOT, 'index.html')
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)
    simple_text = manager.build_simple_text_from_html(html_content)
    with open(os.path.join(settings.MEDIA_ROOT, 'simple_text.txt'), 'w', encoding='utf-8') as file:
        file.write(simple_text)
    print(f"Successfully Done")

def test_chunking():
    html_file_path = os.path.join(settings.MEDIA_ROOT, 'index.html')
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)
    chunks = manager.build_chunks(text=html_content, max_chunk_size=1000)
    for i, chunk in enumerate(chunks):
        html_src = chunk["html"]
        simple_text = chunk["text"]
        with open(os.path.join(settings.MEDIA_ROOT, f'chunk_{i}.html'), 'w', encoding='utf-8') as file:
            file.write(html_src)
        with open(os.path.join(settings.MEDIA_ROOT, f'chunk_{i}.txt'), 'w', encoding='utf-8') as file:
            file.write(simple_text)
    print(f"Successfully Done")

def test_ai_tts():
    manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)
    # Simulate SSML tags for OpenAI TTS
    my_var = "HEY GUYS!!!!!!"
    text = f"""
        "{my_var} ... "
        "I am SO EXCITED to speak with you today. "
        "    This is a demonstration (with a higher pitch) of OpenAI's text-to-speech capabilities. "
        "Can you hear the happiness in my voice? "
        "Let's make this a WONDERFUL EXPERIENCE together!"
    """
    audio_bytes = manager.tts(text=text, voice="nova", audio_format="mp3")
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'audio.mp3')
    with open(audio_file_path, 'wb') as file:
        file.write(audio_bytes)
    print(manager.get_cost())
    print(f"Successfully Done")

def test_ai_stt():
    manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)
    audio_file_path = os.path.join(settings.MEDIA_ROOT, 'audio.mp3')
    with open(audio_file_path, 'rb') as file:
        audio_bytes = file.read()
    text = manager.stt(audio_input=audio_bytes, input_type="bytes")
    print(f"Transcribed Text: {text}")

def test_google_add_message():
    manager = GoogleAIManager(api_key=settings.GOOGLE_API_KEY)
    manager.add_message("user", text="Hello, Google!")
    manager.add_message("assistant", text="Hello, How are you?")
    manager.add_message("system", text="You are a helpful assistant.")
    manager.add_message("user", text="Can you tell me a joke?")
    manager.add_message("user", text="This is a joke for you.")
    manager.add_message("system", text="You have to build a joke.")
    print(manager.prompt)

def test_google_generate_response():
    manager = GoogleAIManager(api_key=settings.GOOGLE_API_KEY)
    manager.add_message("user", text="Tell me a joke.")
    response = manager.generate_response()
    print(f"Response: {response}")

def test_google_tts():
    manager = GoogleAIManager(api_key=settings.GOOGLE_API_KEY)
    text = (
        """<speak>\n"
        "Hello, Google!\n"
        "<break time=\"500ms\"/>\n"
        "<emphasis level=\"strong\">This is a demonstration of speech synthesis.</emphasis>\n"
        "<break time=\"300ms\"/>\n"
        "<prosody pitch=\"+2st\" rate=\"slow\">You can control pitch and speaking rate with SSML prosody tags.</prosody>\n"
        "<break time=\"400ms\"/>\n"
        "<prosody pitch=\"-2st\" rate=\"fast\">Now, let's try a lower pitch and faster rate.</prosody>\n"
        "<break time=\"300ms\"/>\n"
        "<emphasis level=\"moderate\">SSML makes your TTS output more expressive!</emphasis>\n"
        "<break time=\"500ms\"/>\n"
        "Thank you for listening.\n"
        "</speak>"""
    )
    audio_bytes = manager.tts(text=text, voice_name="en-US-Wavenet-D", audio_encoding=texttospeech.AudioEncoding.MP3)
    audio_file_path = os.path.join("/websocket_tmp/google_tts", 'tts_audio.mp3')
    with open(audio_file_path, 'wb') as file:
        file.write(audio_bytes)
    print(f"Successfully Done")

def test_google_stt():
    manager = GoogleAIManager(api_key=settings.GOOGLE_API_KEY)
    audio_file_path = os.path.join("/websocket_tmp/google_tts", 'tts_audio.mp3')
    with open(audio_file_path, 'rb') as file:
        audio_bytes = file.read()
        text = manager.stt(
            audio_bytes=audio_bytes,
            encoding=speech.RecognitionConfig.AudioEncoding.MP3,
            file_path=audio_file_path
        )
    print(manager.get_cost())
    print(f"Transcribed Text: {text}")

def test_document_ai_ocr():
    manager = OCRManager(
        google_cloud_project_id=settings.GOOGLE_CLOUD_DOCUMENT_AI_PROJECT_ID,
        google_cloud_location=settings.GOOGLE_CLOUD_DOCUMENT_AI_LOCATION,
        google_cloud_processor_id=settings.GOOGLE_CLOUD_DOCUMENT_AI_PROCESSOR_ID
    )
    pdf_file_path = os.path.join("/websocket_tmp/texts/", 'The Data Science Handbook.pdf')
    png_bytes = manager.convert_pdf_page_to_png_bytes(pdf_file_path, page_number=21)
    html_output = manager.ocr_using_document_ai(base64.b64encode(png_bytes).decode('utf-8'))
    with open(os.path.join("/websocket_tmp/texts/", 'document_ai_output.html'), 'w', encoding='utf-8') as file:
        file.write(html_output)
    print(f"Successfully Done!")

def test_ai_manager():
    test_document_ai_ocr()