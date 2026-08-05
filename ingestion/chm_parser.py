import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any

class CHMParser:
    """Decompiles and parses Windows CHM (Compiled HTML Help) manuals into structured topic documents."""

    def parse_chm(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Decompiles a .chm file using Windows built-in hh.exe tool and parses HTML topic pages.
        Returns a list of topic objects:
        - text: extracted text content of topic
        - page_number: 1-indexed topic index
        - total_pages: total topic pages in CHM
        - topic_title: title/heading of the HTML page
        - file_name: basename of CHM file
        - file_path: full path to CHM file
        """
        chm_path = Path(file_path).resolve()
        if not chm_path.exists():
            raise FileNotFoundError(f"CHM file not found: {file_path}")

        # Create temp directory for decompilation
        temp_dir = Path(tempfile.mkdtemp(prefix="chm_decomp_"))
        
        try:
            # Run Windows built-in hh.exe decompiler
            cmd = ["hh.exe", "-decompile", str(temp_dir), str(chm_path)]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

            # Find all extracted html/htm files
            html_files = list(temp_dir.rglob("*.htm")) + list(temp_dir.rglob("*.html"))
            
            if not html_files:
                print(f"[Warning] No HTML files extracted from {chm_path.name}")
                return []

            from bs4 import BeautifulSoup

            topics = []
            total_topics = len(html_files)

            for idx, html_file in enumerate(html_files):
                try:
                    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
                        soup = BeautifulSoup(f.read(), "html.parser")

                    # Remove script and style tags
                    for elem in soup(["script", "style", "nav", "footer"]):
                        elem.extract()

                    # Extract title
                    title_elem = soup.find("title") or soup.find("h1") or soup.find("h2")
                    topic_title = title_elem.get_text().strip() if title_elem else html_file.stem

                    text = soup.get_text(separator=" ").strip()

                    # Clean up multiple whitespaces
                    clean_text = " ".join(text.split())

                    if clean_text and len(clean_text) > 30:  # ignore tiny navigation stubs
                        topics.append({
                            "text": f"Topic: {topic_title}\n{clean_text}",
                            "page_number": idx + 1,
                            "total_pages": total_topics,
                            "topic_title": topic_title,
                            "file_name": chm_path.name,
                            "file_path": str(chm_path)
                        })
                except Exception as page_err:
                    continue

            return topics

        finally:
            # Clean up temp folder
            shutil.rmtree(temp_dir, ignore_errors=True)
