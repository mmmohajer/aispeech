from django.conf import settings
import json
import base64
from google.cloud import texttospeech

from ai.utils.open_ai_manager import OpenAIManager
from ai.utils.google_ai_manager import GoogleAIManager
from ai.utils.audio_manager import AudioManager
from websocket.consumers.base import BaseConsumer

class ChatBotConsumer(BaseConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)
        self.google_manager = GoogleAIManager(api_key=settings.GOOGLE_API_KEY)

    def _write_file(self, path, data):
        with open(path, "wb") as f:
            f.write(data)
    
    async def _data_handler(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
                if "type" in data and data["type"] == "audio":
                    await self._audio_handler(data)
            except json.JSONDecodeError:
                await self._send_json({"error": "Invalid JSON format"})
                return
    
    async def _audio_handler(self, data):
        try:
            chunk_id = int(data.get("chunk_id", 0))
            audio_bytes = base64.b64decode(data.get("voice_chunk", ""))
            audio_manager = AudioManager()
            wav_data = await self._run_blocking(audio_manager.convert_webm_to_wav, audio_bytes)
            processed_wav = await self._run_blocking(audio_manager.skip_seconds_wav, wav_data, chunk_id * 60)
            filtered_wav = await self._run_blocking(audio_manager.preprocess_wav, processed_wav)
            open_ai_text = await self._run_blocking(self.openai_manager.stt, filtered_wav, input_type='bytes')
            stt_chunks = self.openai_manager.build_chunks(text=open_ai_text, max_chunk_size=1000)
            
            translated_text = ""
            self.openai_manager.add_message("system", text="You are a helpful assistant that translates text chunks.")
            self.openai_manager.add_message("system", text="You are given a chunk that has been processed from STT, so it might have some issues. First, try to improve the chunk if you feel TTS has trouble building meaningful sentences. Then, translate the improved chunk to English.")
            self.openai_manager.add_message("system", text="You are provided with: previous_chunk, cur_chunk, next_chunk, and a summary of the chunk. Your duty is to translate only the cur_chunk to English, but you may improve the text from your understanding using the context.")
            self.openai_manager.add_message("system", text="Use the previous_chunk and next_chunk, plus the summary, only to help you understand and improve the cur_chunk before translating it. Output only the improved and translated cur_chunk in English.")
            summary = await self._run_blocking(self.openai_manager.summarize, open_ai_text, max_summary_input=15000, max_length=1000, max_chunk_size=1000)
            for i, chunk in enumerate(stt_chunks):
                previous_chunk = stt_chunks[i-1]["text"] if i > 0 else ""
                cur_chunk = chunk["text"]
                next_chunk = stt_chunks[i+1]["text"] if i < len(stt_chunks)-1 else ""
                self.openai_manager.add_message("system", text=f"previous_chunk: {previous_chunk}")
                self.openai_manager.add_message("system", text=f"cur_chunk: {cur_chunk}")
                self.openai_manager.add_message("system", text=f"next_chunk: {next_chunk}")
                self.openai_manager.add_message("system", text=f"summary: {summary}")
                translated = self.openai_manager.generate_response()
                translated_text += translated + " "

            new_audio_bytes = await self._run_blocking(
                self.google_manager.tts,
                translated_text,
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                language_code="en-US"
            )
            await self._run_blocking(self._write_file, f"/websocket_tmp/me/chunk_{chunk_id}.wav", processed_wav)
            await self._run_blocking(self._write_file, f"/websocket_tmp/ai/chunk_{chunk_id}.wav", new_audio_bytes)

            metadata = {
                "type": "audio",
                "chunk_id": chunk_id,
                "text": translated_text,
                "language_code": "en-US"
            }
            await self._send_json(metadata)
        except Exception as e:
            print(e)
            await self._send_json({"error": f"Audio processing error: {str(e)}"})

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
               await self._data_handler(text_data)
        except Exception as e:
            print(e)