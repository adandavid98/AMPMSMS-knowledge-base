from pathlib import Path
from typing import List, Dict, Any

from .pdf_parser import PDFParser
from .chm_parser import CHMParser
from .chunker import TextChunker

def parse_document(file_path: str) -> List[Dict[str, Any]]:
    """
    Unified document parser handling both .pdf and .chm files.
    Returns list of page/topic dictionaries.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        parser = PDFParser()
        return parser.parse_pdf(file_path)
    elif suffix == ".chm":
        parser = CHMParser()
        return parser.parse_chm(file_path)
    elif suffix in [".html", ".htm"]:
        try:
            from bs4 import BeautifulSoup
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for elem in soup(["script", "style", "nav", "footer"]):
                elem.extract()
            title_elem = soup.find("title") or soup.find("h1") or soup.find("h2")
            title = title_elem.get_text().strip() if title_elem else path.stem
            clean_text = " ".join(soup.get_text(separator=" ").split())
            return [{
                "text": f"Topic: {title}\n{clean_text}",
                "page_number": 1,
                "total_pages": 1,
                "topic_title": title,
                "file_name": path.name,
                "file_path": str(path)
            }]
        except Exception as e:
            print(f"[Error] Failed to parse HTML file {path.name}: {e}")
            return []
    elif suffix in [".txt", ".log"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            title = path.stem.replace("_", " ").title()
            return [{
                "text": f"Document: {path.name}\n{content}",
                "page_number": 1,
                "total_pages": 1,
                "topic_title": title,
                "file_name": path.name,
                "file_path": str(path)
            }]
        except Exception as e:
            print(f"[Error] Failed to parse text file {path.name}: {e}")
            return []
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported formats: .pdf, .chm, .html, .htm, .txt, .log")

__all__ = ["PDFParser", "CHMParser", "TextChunker", "parse_document"]
