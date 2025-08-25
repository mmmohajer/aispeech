import re
import random

from ai.utils.chunk_manager import ChunkPipeline

class BaseAIManager:
    """
    Base class for AI managers.
    ai_type (str): The type of AI being used (e.g., "open_ai"); options are "open_ai", "google".
    """
    def __init__(self, ai_type="open_ai"):
        self.messages = []
        self.prompt = ""
        self.cost = 0
        self.ai_type = ai_type

    def _clean_code_block(self, response_text):
        pattern = r"^```(?:json|html)?\n?(.*)```$"
        match = re.match(pattern, response_text.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        return response_text.strip()
    
    def _random_generator(self, length=16):
        """
        Generate a random string of specified length.
        
        Args:
            length (int): Length of the random string. Default is 16.
        
        Returns:
            str: Randomly generated string.
        
        Example:
            token = self._random_generator(8)
        """
        characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(random.choice(characters) for _ in range(length))
    
    def get_cost(self):
        """
        Get the total accumulated cost of API calls.

        Returns:
            float: Total cost in USD.

        Example:
            total = manager.get_cost()
        """
        return self.cost

    def clear_cost(self):
        """
        Reset the accumulated cost to zero.

        Returns:
            None

        Example:
            manager.clear_cost()
        """
        self.cost = 0

    def clear_messages(self):
        """
        Clear the message history.

        Returns:
            None

        Example:
            manager.clear_messages()
        """
        self.messages = []
        self.prompt = ""

    def build_simple_text_from_html(self, html_src):
        """
        Convert HTML content to plain text.
        
        Args:
            html (str): The HTML content to convert.
        
        Returns:
            str: The plain text representation.
        """
        chunk_pipeline = ChunkPipeline()
        text = chunk_pipeline.process(html_src, "get_text")
        return text

    def build_chunks(self, text, max_chunk_size=1000, chunk_mode="html_aware"):
        """
        Chunk text into manageable pieces for processing.
        
        Args:
            text (str): The input text to chunk.
            max_chunk_size (int): Maximum size of each chunk. Default is 1000.
        
        Returns:
            list: List of chunk dicts with 'html' and 'text' keys.
        
        Example:
            chunks = manager.build_chunks(long_text, max_chunk_size=500)
        """
        chunk_pipeline = ChunkPipeline(max_text_chars=max_chunk_size, backtrack=300)
        chunks = chunk_pipeline.process(text, "get_chunks", chunk_mode)
        for i in range(len(chunks) - 1):
            head, tail = chunk_pipeline.chunker.get_incomplete_end_html_aware(chunks[i]["html"])
            if tail:
                chunks[i]["html"] = head
                chunks[i]["text"] = self.build_simple_text_from_html(head)
                chunks[i + 1]["html"] = tail + chunks[i + 1]["html"]
                chunks[i + 1]["text"] = self.build_simple_text_from_html(tail + chunks[i + 1]["text"])
        return chunks
    
    def add_message(self, *args, **kwargs):
        """
        Abstract method for adding a new message to build the prompt.
        Must be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement add_message.")

    def generate_response(self, *args, **kwargs):
        """
        Abstract method for generating a response from the AI model.
        Must be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must implement generate_response.")
    
    def summarize(self, text, max_length=1000, max_chunk_size=1000):
        """
        Iteratively summarize a long text by processing it chunk by chunk and accumulating the summary.
        For each chunk, the method combines the previous summary (if any) with the current chunk and asks the AI model to summarize them together.
        This process continues for all chunks, so the summary grows and evolves as more of the text is processed.

        Args:
            text (str): The text to summarize.
            max_length (int): Maximum number of tokens for each summary step. Default is 1000.
            max_chunk_size (int): Maximum size of each chunk. Default is 1000.

        Returns:
            str: The final accumulated summary of the entire text.

        Example:
            summary = manager.summarize(long_text)
        """
        chunks = self.build_chunks(text, max_chunk_size=max_chunk_size)
        summary = ""
        i = 0
        for chunk in chunks:
            i += 1
            print(f"Processing chunk {i}/{len(chunks)}")
            input_text = (summary + "\n" + chunk["text"]).strip() if summary else chunk["text"]
            messages = [
                {"role": "system", "content": "You are a summarization expert. Summarize the following text."},
                {"role": "user", "content": input_text}
            ]
            prompt = f"Summarize the following text in at most {max_length} tokens:\n\n{input_text}"
            if self.ai_type == "open_ai":
                response = self.generate_response(max_token=max_length, messages=messages)
            elif self.ai_type == "google":
                response = self.generate_response(max_token=max_length, prompt=prompt)
            summary = response
        return summary
    
    def summarize_for_translation(self, text, max_length=1000, max_chunk_size=1000):
        """
        Iteratively summarize and interpret a long text chunk by chunk, accumulating summary and clarifications for translation.
        For each chunk, instruct the AI to:
        - Summarize the chunk and previous summary.
        - Identify any ambiguous phrases or unclear meanings and note them.
        - If context from later chunks clarifies previous ambiguities, update the summary to reflect the improved understanding.
        This helps the translation process by tracking and clarifying phrases as more context is available.

        Args:
            text (str): The text to summarize and interpret for translation.
            max_length (int): Maximum number of tokens for each summary step. Default is 1000.
            max_chunk_size (int): Maximum size of each chunk. Default is 1000.

        Returns:
            str: The final accumulated summary and clarifications for translation.

        Example:
            summary = manager.summarize_for_translation(long_text)
        """
        chunks = self.build_chunks(text, max_chunk_size=max_chunk_size)
        summary = ""
        i = 0
        for chunk in chunks:
            i += 1
            print(f"Processing chunk {i}/{len(chunks)}")
            input_text = (summary + "\n" + chunk["text"]).strip() if summary else chunk["text"]
            system_prompt = (
                "You are a translation assistant. The purpose of this summarization is to provide hints and context needed for better translation of words, phrases, and expressions used in the text, not a general summary. "
                "For the following text, do the following: "
                "1. Summarize only the information relevant for accurate translation. "
                "2. Identify any ambiguous phrases or unclear meanings and note them. "
                "3. If you now understand the meaning of a previously ambiguous phrase, clarify it in this summary. "
                "4. Track and update clarifications as more context is available. "
                "Output only the summary and clarifications that help with translation."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text}
            ]
            prompt = (
                "Summarize and interpret the following text in at most {max_length} tokens. "
                "Identify ambiguous phrases and clarify them if possible as context improves.\n\n{input_text}"
            )
            if self.ai_type == "open_ai":
                response = self.generate_response(max_token=max_length, messages=messages)
            elif self.ai_type == "google":
                response = self.generate_response(max_token=max_length, prompt=prompt)
            summary = response
        return summary
    
    def summarize_for_manipulation(self, text, manipulation_type="improve_fluency", max_length=1000, max_chunk_size=1000):
        """
        Build a summary and guidance for AI to manipulate documentation, with options for tone, style, and improvement hints.
        For each chunk, instruct the AI to:
        - Summarize the chunk and previous summary.
        - Identify weaknesses, areas for improvement, and provide actionable hints.
        - Suggest how to change tone, style, or structure based on manipulation_type (e.g., academic, formal, informal, conversational, poetic, improve fluency, add citations, etc).
        - Track and update guidance as more context is available.

        Args:
            text (str): The text to summarize and guide for manipulation.
            manipulation_type (str): Desired manipulation style (e.g., 'academic', 'formal', 'informal', 'conversational', 'poetic', 'improve_fluency', 'add_citations').
            max_length (int): Maximum number of tokens for each summary step. Default is 1000.
            max_chunk_size (int): Maximum size of each chunk. Default is 1000.

        Returns:
            str: The final accumulated summary and manipulation guidance.

        Example:
            summary = manager.summarize_for_manipulation(long_text, manipulation_type='academic')
        """
        chunks = self.build_chunks(text, max_chunk_size=max_chunk_size)
        summary = ""
        i = 0
        for chunk in chunks:
            i += 1
            print(f"Processing chunk {i}/{len(chunks)}")
            input_text = (summary + "\n" + chunk["text"]).strip() if summary else chunk["text"]
            system_prompt = (
                f"You are a documentation improvement assistant. The purpose of this summarization is to provide hints and guidance for manipulating the text to better match the desired style: {manipulation_type}. "
                "For the following text, do the following: "
                "1. Summarize only the information relevant for improving or changing the tone, literature, and structure. "
                "2. Identify weaknesses, awkward phrasing, poor punctuation, or lack of fluency, and suggest improvements. "
                "3. If manipulation_type is 'academic', make sure to have clear citations if needed, formal structure, and technical vocabulary. "
                "4. If manipulation_type is 'formal', make the text more professional and polished. "
                "5. If manipulation_type is 'informal' or 'conversational', make the text more relaxed and friendly. "
                "6. If manipulation_type is 'poetic', suggest ways to make the text more lyrical or artistic. "
                "7. For any other manipulation_type, provide specific guidance to achieve the desired style. "
                "8. After each paragraph, add hints about weaknesses and how to improve the text. "
                "Output only the summary and actionable guidance for manipulation."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text}
            ]
            prompt = (
                f"{system_prompt}\n"
                f"Summarize and provide manipulation guidance for the following text in at most {max_length} tokens. "
                f"Manipulation type: {manipulation_type}. "
                "Identify weaknesses and suggest improvements as context improves.\n\n{input_text}"
            )
            if self.ai_type == "open_ai":
                response = self.generate_response(max_token=max_length, messages=messages)
            elif self.ai_type == "google":
                response = self.generate_response(max_token=max_length, prompt=prompt)
            summary = response
        return summary

    def translate(self, text, target_language, max_length_for_general_summary=2000, max_chunk_size_for_general_summary=15000, max_length_for_translation_summary=5000, max_chunk_size_for_translation_summary=15000, max_chunk_size=1000, max_translation_tokens=5000):
        """
        Translate text to the target language using context-aware chunking and translation.

        This method first builds a general summary and a translation-focused summary of the input text. It then splits the text into chunks and translates each chunk individually, providing the previous chunk, current chunk, next chunk, general summary, and translation summary as context for each translation step.

        Special translation rules:
        - If the input is HTML, do not translate or modify any HTML tags; keep them as is, even if incomplete.
        - If a chunk contains suspicious or unrelated words (e.g., OCR errors), skip or replace them with meaningful words/phrases.
        - If a chunk/block is only a page number, page title, or footer, ignore it in the translation.
        - Ensure the translation is fluent and natural for the target language, preserving the original meaning.

        Args:
            text (str): The input text (can be HTML).
            target_language (str): The language code to translate to (e.g., 'en', 'fr', 'fa').
            max_length_for_general_summary (int): Maximum tokens for general summary. Default is 2000.
            max_chunk_size_for_general_summary (int): Maximum chunk size for general summary. Default is 15000.
            max_length_for_translation_summary (int): Maximum tokens for translation summary. Default is 5000.
            max_chunk_size_for_translation_summary (int): Maximum chunk size for translation summary. Default is 15000.
            max_chunk_size (int): Maximum size of each chunk for translation. Default is 1000.
            max_translation_tokens (int): Maximum tokens for each translation step. Default is 5000.

        Returns:
            str: The translated text.

        Example:
            translated = manager.translate(text, target_language='en')
        """
        general_summary = self.summarize(text, max_length=max_length_for_general_summary, max_chunk_size=max_chunk_size_for_general_summary)
        translation_summary = self.summarize_for_translation(text, max_length=max_length_for_translation_summary, max_chunk_size=max_chunk_size_for_translation_summary)
        chunks = self.build_chunks(text, max_chunk_size=max_chunk_size)
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"Translating chunk {i}/{len(chunks)}")
            previous_chunk = chunks[i-1]["html"] if i > 0 else ""
            cur_chunk = chunk["html"]
            next_chunk = chunks[i+1]["html"] if i < len(chunks)-1 else ""
            system_prompt = (
                f"You are a professional translator. Your task is to translate only the current chunk to {target_language}.\n"
                "You are given the general summary, translation summary, previous chunk, current chunk, and next chunk for context.\n"
                "Do NOT translate or modify any HTML tags; keep them as is, even if incomplete.\n"
                "If you see suspicious/unrelated words (e.g., OCR errors), skip or replace them with meaningful words/phrases.\n"
                "If a chunk/block is only a page number, page title, or footer, ignore it in the translation.\n"
                "Make sure the translation is fluent and natural for the target language, preserving the original meaning."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"General summary: {general_summary}\n"
                    f"Translation summary: {translation_summary}\n"
                    f"Previous chunk: {previous_chunk}\n"
                    f"Current chunk: {cur_chunk}\n"
                    f"Next chunk: {next_chunk}\n"
                )}
            ]
            if self.ai_type == "open_ai":
                translated = self.generate_response(max_token=max_translation_tokens, messages=messages)
            elif self.ai_type == "google":
                prompt = (
                    f"{system_prompt}\n"
                    f"General summary: {general_summary}\n"
                    f"Translation summary: {translation_summary}\n"
                    f"Previous chunk: {previous_chunk}\n"
                    f"Current chunk: {cur_chunk}\n"
                    f"Next chunk: {next_chunk}\n"
                )
                translated = self.generate_response(max_token=max_translation_tokens, prompt=prompt)
            translated_chunks.append(translated)
        return "".join(translated_chunks)

    def manipulate_text(self, text, manipulation_type="improve_fluency", target_language=None, max_length_for_general_summary=2000, max_chunk_size_for_general_summary=15000, max_length_for_manipulation_summary=5000, max_chunk_size_for_manipulation_summary=15000, max_chunk_size=1000, max_manipulation_tokens=5000):
        """
        Manipulate the input text using context-aware chunking, summaries, and generate HTML output with allowed tags and placeholders.

        This method first builds a general summary and a manipulation-focused summary of the input text. It then splits the text into chunks and manipulates each chunk individually, providing the previous chunk, current chunk, next chunk, general summary, manipulation summary, previous manipulated chunk, and a summary of all previous manipulated chunks as context for each manipulation step.

        The output is in HTML format, using only allowed tags: h1-h6, p, div, a, ul, li, img, video. Images and videos use placeholders with captions.

        Args:
            text (str): The input text to manipulate.
            manipulation_type (str): Desired manipulation style (e.g., 'academic', 'formal', 'informal', 'conversational', 'poetic', 'improve_fluency', 'add_citations').
            target_language (str or None): If set, rewrite the improved version in this language (e.g., 'en', 'fr', 'fa'). If None, keep the original language.
            max_length_for_general_summary (int): Maximum tokens for general summary. Default is 2000.
            max_chunk_size_for_general_summary (int): Maximum chunk size for general summary. Default is 15000.
            max_length_for_manipulation_summary (int): Maximum tokens for manipulation summary. Default is 5000.
            max_chunk_size_for_manipulation_summary (int): Maximum chunk size for manipulation summary. Default is 15000.
            max_chunk_size (int): Maximum size of each chunk for manipulation. Default is 1000.
            max_manipulation_tokens (int): Maximum tokens for each manipulation step. Default is 5000.

        Returns:
            str: The manipulated text in HTML format.

        Example:
            manipulated = manager.manipulate_text(text, manipulation_type='academic', target_language='fr')
        """
        general_summary = self.summarize(text, max_length=max_length_for_general_summary, max_chunk_size=max_chunk_size_for_general_summary)
        manipulation_summary = self.summarize_for_manipulation(text, manipulation_type=manipulation_type, max_length=max_length_for_manipulation_summary, max_chunk_size=max_chunk_size_for_manipulation_summary)
        chunks = self.build_chunks(text, max_chunk_size=max_chunk_size)
        manipulated_chunks = []
        joint_manipulated_summary = ""
        for i, chunk in enumerate(chunks):
            print(f"Manipulating chunk {i}/{len(chunks)}")
            previous_chunk = chunks[i-1]["html"] if i > 0 else ""
            cur_chunk = chunk["html"]
            next_chunk = chunks[i+1]["html"] if i < len(chunks)-1 else ""
            previous_manipulated_chunk = manipulated_chunks[i-1] if i > 0 else ""
            system_prompt = (
                f"You are a professional documentation editor. Your task is to manipulate only the current chunk according to the style: {manipulation_type}.\n"
                + (f"Rewrite the improved version in {target_language}.\n" if target_language else "")
                + "You are given the general summary, manipulation summary, previous chunk, current chunk, next chunk, previous manipulated chunk, and a summary of all previous manipulated chunks for context.\n"
                + "Include only allowed HTML tags: h1-h6, p, div, a, ul, li, img, video.\n"
                + "For images or videos, use a placeholder with a caption.\n"
                + "When reviewing each chunk, use the context to improve writing, consistency, and interpretation.\n"
                + "If you see a header, anchor, paragraph, list, or table, use the correct HTML tag.\n"
                + "Output only the manipulated chunk in HTML format."
            )
            user_content = (
                f"General summary: {general_summary}\n"
                f"Manipulation summary: {manipulation_summary}\n"
                f"Previous chunk: {previous_chunk}\n"
                f"Current chunk: {cur_chunk}\n"
                f"Next chunk: {next_chunk}\n"
                f"Previous manipulated chunk: {previous_manipulated_chunk}\n"
                f"Summary of all previous manipulated chunks: {joint_manipulated_summary}\n"
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            prompt = (
                f"{system_prompt}\n"
                f"General summary: {general_summary}\n"
                f"Manipulation summary: {manipulation_summary}\n"
                f"Previous chunk: {previous_chunk}\n"
                f"Current chunk: {cur_chunk}\n"
                f"Next chunk: {next_chunk}\n"
                f"Previous manipulated chunk: {previous_manipulated_chunk}\n"
                f"Summary of all previous manipulated chunks: {joint_manipulated_summary}\n"
            )
            if self.ai_type == "open_ai":
                manipulated = self.generate_response(max_token=max_manipulation_tokens, messages=messages)
            elif self.ai_type == "google":
                manipulated = self.generate_response(max_token=max_manipulation_tokens, prompt=prompt)
            manipulated_chunks.append(manipulated)
            joint_manipulated_summary = self.summarize(joint_manipulated_summary)
        return "".join(manipulated_chunks)