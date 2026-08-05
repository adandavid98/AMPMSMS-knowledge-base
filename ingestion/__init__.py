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
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported formats: .pdf, .chm")

__all__ = ["PDFParser", "CHMParser", "TextChunker", "parse_document"]
