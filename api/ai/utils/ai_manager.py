import re

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
    
    def summarize(self, text, max_summary_input=15000, max_length=1000, max_chunk_size=1000):
        """
        Summarize a long text using the chat model, chunking if needed.
        
        Args:
            text (str): The text to summarize.
            max_summary_input (int): Max input size for a single summary. Default 15000.
            max_length (int): Max tokens for each summary. Default 1000.
            max_chunk_size (int): Chunk size for splitting text. Default 1000.
        
        Returns:
            str: Summarized text.
        
        Example:
            summary = manager.summarize(long_text)
        """
        def recursive_summarize(text):
            if len(text) <= max_summary_input:
                messages = [
                    {"role": "system", "content": "You are a summarization expert. Summarize the following text."},
                    {"role": "user", "content": text}
                ]
                prompt = f"Summarize the following text in at most {max_length} tokens:\n\n{text}"
                if self.ai_type == "open_ai":
                    response = self.generate_response(max_token=max_length, messages=messages)
                elif self.ai_type == "google":
                    response = self.generate_response(max_token=max_length, prompt=prompt)
                return response
            else:
                chunks = self.build_chunks(text, max_chunk_size=max_chunk_size)
                summaries = []
                for chunk in chunks:
                    messages = [
                        {"role": "system", "content": "You are a summarization expert. Summarize the following text."},
                        {"role": "user", "content": chunk["text"]}
                    ]
                    prompt = f"Summarize the following text in at most {max_length} tokens:\n\n{chunk['text']}"
                    if self.ai_type == "open_ai":
                        response = self.generate_response(max_token=max_length, messages=messages)
                    elif self.ai_type == "google":
                        response = self.generate_response(max_token=max_length, prompt=prompt)
                    summaries.append(response)
                combined = " ".join(summaries)
                return recursive_summarize(combined)
        return recursive_summarize(text)