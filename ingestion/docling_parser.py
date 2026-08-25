import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class DoclingParser:
    """
    Advanced Document Parser using Docling.
    Extracts structured Markdown, preserves tables in GFM format,
    maintains section hierarchy, and detects visual figures/diagrams.
    """

    def __init__(self):
        self._docling_available = False
        try:
            from docling.document_converter import DocumentConverter
            self.converter = DocumentConverter()
            self._docling_available = True
        except ImportError:
            self.converter = None

    def parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parses a PDF file using Docling.
        Returns a list of structured section/page objects.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if not self._docling_available:
            from .pdf_parser import PDFParser
            return PDFParser().parse_pdf(str(path))

        try:
            print(f"[Docling] Converting and analyzing layout for: {path.name}...")
            result = self.converter.convert(str(path))
            doc = result.document

            # Export structured markdown
            markdown_content = doc.export_to_markdown()

            # Split markdown by sections / pages or headers
            sections = self._split_markdown_sections(markdown_content, path)

            if not sections:
                # Fallback to single document container if no headers
                title = path.stem.replace("_", " ").title()
                return [{
                    "text": markdown_content.strip(),
                    "page_number": 1,
                    "total_pages": 1,
                    "topic_title": title,
                    "file_name": path.name,
                    "file_path": str(path),
                    "is_structured_markdown": True
                }]

            return sections

        except Exception as e:
            print(f"[Warning] Docling parse failed for {path.name} ({e}), falling back to PDFParser...")
            from .pdf_parser import PDFParser
            return PDFParser().parse_pdf(str(path))

    def _split_markdown_sections(self, markdown_text: str, file_path: Path) -> List[Dict[str, Any]]:
        """
        Splits markdown document into logical sections based on H1/H2 headers (# and ##).
        Preserves Markdown tables within their respective sections.
        """
        lines = markdown_text.split("\n")
        sections = []
        current_section = []
        current_title = file_path.stem.replace("_", " ").title()
        section_idx = 1

        for line in lines:
            if line.startswith("# ") or line.startswith("## "):
                if current_section:
                    sec_text = "\n".join(current_section).strip()
                    if len(sec_text) > 30:
                        sections.append({
                            "text": f"Section: {current_title}\n\n{sec_text}",
                            "page_number": section_idx,
                            "total_pages": 0,  # Updated at the end
                            "topic_title": current_title,
                            "file_name": file_path.name,
                            "file_path": str(file_path),
                            "is_structured_markdown": True
                        })
                        section_idx += 1
                    current_section = []
                current_title = line.lstrip("#").strip()
            current_section.append(line)

        # Append last section
        if current_section:
            sec_text = "\n".join(current_section).strip()
            if len(sec_text) > 30:
                sections.append({
                    "text": f"Section: {current_title}\n\n{sec_text}",
                    "page_number": section_idx,
                    "total_pages": 0,
                    "topic_title": current_title,
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "is_structured_markdown": True
                })

        total_sections = max(len(sections), 1)
        for s in sections:
            s["total_pages"] = total_sections

        return sections
