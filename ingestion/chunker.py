import re
from typing import List, Dict, Any
from config import CHUNK_SIZE, CHUNK_OVERLAP, VALID_CATEGORIES

class TextChunker:
    """
    Splits document sections and pages into semantically cohesive,
    overlapping chunks while preserving Markdown tables and section titles.
    """

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes parsed document pages/sections and returns a list of chunk dictionaries.
        """
        all_chunks = []

        for page in pages:
            text = page.get("text", "")
            if not text.strip():
                continue

            topic_title = page.get("topic_title", "")
            is_markdown = page.get("is_structured_markdown", False)

            if is_markdown:
                page_chunks = self._split_markdown(text, topic_title)
            else:
                page_chunks = self._split_text(text)

            category = self._classify_category(text, page.get("file_name", ""))

            for idx, chunk_text in enumerate(page_chunks):
                chunk_id = f"{page['file_name']}_p{page['page_number']}_c{idx+1}"
                all_chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "file_name": page["file_name"],
                        "file_path": page["file_path"],
                        "page_number": page["page_number"],
                        "total_pages": page["total_pages"],
                        "category": category,
                        "chunk_index": idx + 1,
                        "topic_title": topic_title
                    }
                })

        return all_chunks

    def _split_markdown(self, markdown_text: str, topic_title: str) -> List[str]:
        """
        Splits markdown text keeping tables and paragraphs intact where possible.
        """
        blocks = markdown_text.split("\n\n")
        chunks = []
        current_block = []
        current_word_count = 0

        header_prefix = f"Topic: {topic_title}\n\n" if topic_title else ""

        for b in blocks:
            b_words = len(b.split())
            if current_word_count + b_words > self.chunk_size and current_block:
                chunk_content = "\n\n".join(current_block).strip()
                if not chunk_content.startswith("Topic:") and header_prefix:
                    chunk_content = header_prefix + chunk_content
                chunks.append(chunk_content)
                current_block = [b]
                current_word_count = b_words
            else:
                current_block.append(b)
                current_word_count += b_words

        if current_block:
            chunk_content = "\n\n".join(current_block).strip()
            if not chunk_content.startswith("Topic:") and header_prefix:
                chunk_content = header_prefix + chunk_content
            chunks.append(chunk_content)

        return chunks or [markdown_text]

    def _split_text(self, text: str) -> List[str]:
        """Splits text into overlapping words/tokens windows."""
        words = text.split()
        if len(words) <= self.chunk_size:
            return [" ".join(words)]

        chunks = []
        start = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            if end >= len(words):
                break
            start += step

        return chunks

    def _classify_category(self, text: str, file_name: str) -> str:
        """Determines the document category based on filename and text keywords."""
        content_lower = (file_name + " " + text).lower()

        if any(k in content_lower for k in ["verifone", "m400", "pin pad", "pinpad", "mx915", "pos terminal", "vx520"]):
            return "Verifone Hardware"
        elif any(k in content_lower for k in ["buypass", "fiserv", "credit auth", "host response", "bin table", "settlement"]):
            return "Buypass Config"
        elif any(k in content_lower for k in ["sms software", "loc software", "loc sms", "register.ini", "pos.ini", "touch"]):
            return "SMS Software"
        elif any(k in content_lower for k in ["server", "sql", "database", "backup", "store server", "master"]):
            return "Server Config"
        elif any(k in content_lower for k in ["network", "ip address", "lan", "wan", "port", "switch", "router", "gateway", "dhcp"]):
            return "Network / Connectivity"
        else:
            return "General"
