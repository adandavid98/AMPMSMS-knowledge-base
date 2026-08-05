import re
from typing import List, Dict, Any
from config import CHUNK_SIZE, CHUNK_OVERLAP, VALID_CATEGORIES

class TextChunker:
    """Splits document pages into overlapping text chunks and tags them with metadata."""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes parsed PDF pages and returns a list of chunk dictionaries.
        Each chunk contains:
        - chunk_id: unique identifier string
        - text: the text content of the chunk
        - metadata: dict containing file_name, page_number, category, chunk_index
        """
        all_chunks = []

        for page in pages:
            text = page.get("text", "")
            if not text.strip():
                continue

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
                        "chunk_index": idx + 1
                    }
                })

        return all_chunks

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

        if any(k in content_lower for k in ["verifone", "m400", "pin pad", "pinpad", "mx915", "pos terminal"]):
            return "Verifone Hardware"
        elif any(k in content_lower for k in ["buypass", "fiserv", "credit auth", "host response", "bin table"]):
            return "Buypass Config"
        elif any(k in content_lower for k in ["sms software", "loc software", "loc sms", "register.ini", "pos.ini"]):
            return "SMS Software"
        elif any(k in content_lower for k in ["server", "sql", "database", "backup", "store server", "master"]):
            return "Server Config"
        elif any(k in content_lower for k in ["network", "ip address", "lan", "wan", "port", "switch", "router", "gateway"]):
            return "Network / Connectivity"
        else:
            return "General"
