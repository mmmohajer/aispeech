from google.cloud import speech, texttospeech, vision
from google.generativeai import GenerativeModel, configure
import tiktoken

from ai.utils.ai_manager import BaseAIManager
from ai.utils.audio_manager import AudioManager

class GoogleAIManager(BaseAIManager):
    def __init__(self, api_key=None):
        """
        Initialize the GoogleAIManager.

        Args:
            api_key (str): API key for Generative Language API (PaLM/Gemini).
            credentials_path (str): Path to Google service account JSON for other APIs.

        Returns:
            None
        """
        super().__init__(ai_type="google")
        if api_key:
            configure(api_key=api_key)
        self.speech_client = speech.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
        self.vision_client = vision.ImageAnnotatorClient()
        self.model = GenerativeModel("gemini-pro") if api_key else None
        self.GOOGLE_AI_PRICING = {
            "gemini-pro": {
                "input_per_1k_token": 0.0005,
                "output_per_1k_token": 0.0015,
            },
            "gemini-pro-vision": {
                "input_per_1k_token": 0.001,
                "output_per_1k_token": 0.003,
                "image_per_1_image": 0.002,
            },
            "speech-to-text": {
                "audio_stt_per_1_minute": 0.006,
            },
            "text-to-speech": {
                "tts_standard_per_1k_char": 0.016,
                "tts_premium_per_1k_char": 0.024,
            },
            "vision": {
                "image_per_1_image": 0.0015,
            },
        }

    def add_message(self, role, text=None, max_history=5):
        """
        Add a message to the conversation history. For Google Gemini, concatenates the last max_history turns in order,
        and summarizes earlier ones with an explanation at the beginning of the prompt.

        Args:
            role (str): One of 'system', 'user', 'assistant'.
            text (str): The text content.
            max_history (int): Maximum number of messages to keep in history. Default is 5.

        Returns:
            None

        Example:
            manager.add_message("user", text="Hello!")
        """
        if role not in ["system", "user", "assistant"]:
            return
        msg_text = text if text is not None else ""
        self.messages.append({"role": role, "content": msg_text})
        if len(self.messages) > max_history:
            old_msgs = self.messages[:-max_history]
            recent_msgs = self.messages[-max_history:]
            summary_lines = []
            system_lines = []
            for msg in old_msgs:
                if msg["role"] == "user":
                    summary_lines.append(f"User said: {msg['content']}")
                elif msg["role"] == "assistant":
                    summary_lines.append(f"Assistant said: {msg['content']}")
                elif msg["role"] == "system":
                    system_lines.append(f"System: {msg['content']}")
            summary_text = self.summarize("\n".join(summary_lines)) if summary_lines else ""
            system_text = "\n".join(system_lines)
            self.prompt = ""
            if summary_text:
                self.prompt += f"This is the summary of past conversations:\n{summary_text}\n"
            if system_text:
                self.prompt += f"System messages:\n{system_text}\n"
            self.prompt += f"\nNow, here are the last {max_history} messages in order:\n"
            for msg in recent_msgs:
                if msg["role"] == "user":
                    self.prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    self.prompt += f"Assistant: {msg['content']}\n"
                elif msg["role"] == "system":
                    self.prompt += f"System: {msg['content']}\n"
        else:
            self.prompt = ""
            for msg in self.messages:
                if msg["role"] == "user":
                    self.prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    self.prompt += f"Assistant: {msg['content']}\n"
                elif msg["role"] == "system":
                    self.prompt += f"System: {msg['content']}\n"
    
    def generate_response(self, max_token=2000, prompt=None):
        """
        Generate a response from the OpenAI chat model.
        
        Args:
            max_token (int): Maximum number of tokens in the response. Default is 2000.
            messages (list): List of message dicts. If None, uses internal history.
        
        Returns:
            str: The assistant's response text.
        
        Example:
            reply = manager.generate_response(max_token=500)
        """
        if not self.model:
            raise RuntimeError("Generative Language API not configured.")
        use_prompt = prompt if prompt is not None else getattr(self, "prompt", None)
        if not use_prompt:
            raise ValueError("Prompt is empty. Add messages before generating a response.")
        response = self.model.generate_content(use_prompt, generation_config={"max_output_tokens": max_token})
        enc = tiktoken.get_encoding("cl100k_base") 
        input_token_count = len(enc.encode(prompt))
        output_token_count = len(enc.encode(response.text))
        self.cost += (input_token_count / 1000) * self.GOOGLE_AI_PRICING["gemini-pro"]["input_per_1k_token"]
        self.cost += (output_token_count / 1000) * self.GOOGLE_AI_PRICING["gemini-pro"]["output_per_1k_token"]
        return response.text
    
    def stt(self, audio_bytes, language_code='en-US', sample_rate_hertz=16000):
        """
        Perform speech-to-text using Google Cloud Speech-to-Text API.

        Args:
            audio_bytes (bytes): The input audio data.
            language_code (str): Language code of the audio. Default is 'en-US'.
            sample_rate_hertz (int): Sample rate in Hz. Default is 16000.

        Returns:
            dict: The transcription result.
        """
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate_hertz,
            language_code=language_code,
        )
        response = client.recognize(config=config, audio=audio)

        audio_manager = AudioManager()
        duration_seconds = audio_manager.get_wav_duration(audio_bytes)
        duration_minutes = duration_seconds / 60
        price_per_minute = self.GOOGLE_AI_PRICING["speech-to-text"]["audio_stt_per_1_minute"]
        cost = duration_minutes * price_per_minute
        self.cost += cost
        return response
    
    def tts(self, text, voice_name="en-US-Wavenet-D", audio_encoding=texttospeech.AudioEncoding.MP3):
        """
        Perform text-to-speech using Google Cloud Text-to-Speech API.

        Args:
            text (str): The text to convert to speech.
            voice_name (str): The name of the voice to use. Default is "en-US-Wavenet-D".
            audio_encoding (str): The audio encoding format. Default is MP3.

        Returns:
            bytes: The audio content in the specified format.
        """
        client = texttospeech.TextToSpeechClient()
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            name=voice_name,
            language_code="en-US",
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
        )
        response = client.synthesize_speech(
            input=input_text,
            voice=voice,
            audio_config=audio_config
        )

        char_count = len(text)
        if "Wavenet" in voice_name:
            price_per_1k = self.GOOGLE_AI_PRICING["text-to-speech"]["tts_premium_per_1k_char"]
        else:
            price_per_1k = self.GOOGLE_AI_PRICING["text-to-speech"]["tts_standard_per_1k_char"]
        cost = (char_count / 1000) * price_per_1k
        self.cost += cost
        return response.audio_content
    
    def generate_image_description(self, image_bytes):
        """
        Generate a description of an image using Google Cloud Vision API.

        Args:
            image_bytes (bytes): The input image data.

        Returns:
            str: The generated description of the image.
        """
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        response = client.label_detection(image=image)
        labels = response.label_annotations
        descriptions = [label.description for label in labels]
        cost = self.GOOGLE_AI_PRICING["vision"]["image_per_1_image"]
        self.cost += cost
        return ", ".join(descriptions)