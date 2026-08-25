import os
from pathlib import Path
from typing import List, Dict, Any

class PDFParser:
    """Extracts page-by-page text and metadata from PDF files."""

    def __init__(self):
        self._fitz_available = False
        try:
            import fitz  # PyMuPDF
            self._fitz_available = True
        except ImportError:
            pass

    def parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parses a PDF file and returns a list of page objects.
        Each page object contains:
        - text: string content of the page
        - page_number: 1-indexed page number
        - total_pages: total pages in document
        - file_name: basename of the file
        - file_path: full path to file
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if self._fitz_available:
            pages = self._parse_with_fitz(path)
        else:
            pages = self._parse_with_pypdf(path)

        # Fallback for scanned/image PDFs with no extractable text stream
        total_text_length = sum(len(p.get("text", "").strip()) for p in pages)
        if total_text_length == 0:
            title = path.stem.replace("_", " ").replace("-", " ").title()
            return [{
                "text": f"Document: {path.name}\nTitle: {title}\n(Scanned PDF Document - Image / Graphic Content)",
                "page_number": 1,
                "total_pages": max(len(pages), 1),
                "topic_title": title,
                "file_name": path.name,
                "file_path": str(path.resolve())
            }]

        return pages

    def _parse_with_fitz(self, path: Path) -> List[Dict[str, Any]]:
        import fitz
        doc = fitz.open(str(path))
        total_pages = len(doc)
        pages = []

        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text").strip()
            pages.append({
                "text": text,
                "page_number": page_num + 1,
                "total_pages": total_pages,
                "file_name": path.name,
                "file_path": str(path.resolve())
            })
        doc.close()
        return pages

    def _parse_with_pypdf(self, path: Path) -> List[Dict[str, Any]]:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        total_pages = len(reader.pages)
        pages = []

        for page_num, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            pages.append({
                "text": text,
                "page_number": page_num + 1,
                "total_pages": total_pages,
                "file_name": path.name,
                "file_path": str(path.resolve())
            })
        return pages
