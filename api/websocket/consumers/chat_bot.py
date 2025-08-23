import functools
from django.conf import settings
import json
import asyncio
import base64

from ai.utils.open_ai_manager import OpenAIManager
from ai.utils.audio_manager import AudioManager
from websocket.consumers.base import BaseConsumer

class ChatBotConsumer(BaseConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_manager = OpenAIManager(model="gpt-4o", api_key=settings.OPEN_AI_SECRET_KEY)

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
            loop = asyncio.get_running_loop()
            wav_data = await loop.run_in_executor(None, audio_manager.convert_webm_to_wav, audio_bytes)
            processed_wav = await loop.run_in_executor(None, audio_manager.skip_seconds_wav, wav_data, chunk_id * 5)
            filtered_wav = await loop.run_in_executor(None, audio_manager.preprocess_wav, processed_wav)
            text = await loop.run_in_executor(
                None,
                functools.partial(self.openai_manager.stt, filtered_wav, input_type='bytes')
            )
            new_audio_bytes = await loop.run_in_executor(
                None,
                functools.partial(self.openai_manager.tts, text, audio_format='mp3')
            )

            await loop.run_in_executor(None, self._write_file, f"/websocket_tmp/me/chunk_{chunk_id}.wav", processed_wav)
            await loop.run_in_executor(None, self._write_file, f"/websocket_tmp/ai/chunk_{chunk_id}.wav", new_audio_bytes)

            metadata = {
                "type": "audio",
                "chunk_id": chunk_id,
                # "text": text
            }
            # metadata["voice_chunk"] = base64.b64encode(new_audio_bytes).decode("utf-8")
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