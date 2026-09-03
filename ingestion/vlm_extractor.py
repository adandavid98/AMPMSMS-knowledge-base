import os
import io
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional

class VLMExtractor:
    """
    Vision-Language Model (VLM) Extractor using Gemini Flash Vision.
    Extracts and generates semantic technical descriptions for screenshots,
    wiring diagrams, flowcharts, and POS display panels.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def describe_image(self, image_data: Any, context_title: str = "") -> Optional[str]:
        """
        Takes raw image bytes, PIL Image, or Base64 string and generates a detailed
        technical caption/description for RAG semantic indexing.
        """
        try:
            import google.generativeai as genai
            import config

            active_key = self.api_key or config.GEMINI_API_KEY
            if not active_key:
                return None

            genai.configure(api_key=active_key)
            from PIL import Image

            pil_img = None
            if isinstance(image_data, str):
                b64_data = image_data.split(",")[-1]
                img_bytes = base64.b64decode(b64_data)
                pil_img = Image.open(io.BytesIO(img_bytes))
            elif isinstance(image_data, bytes):
                pil_img = Image.open(io.BytesIO(image_data))
            elif hasattr(image_data, "save"):
                pil_img = image_data

            if not pil_img:
                return None

            prompt = (
                f"Context: Point of Sale (POS) Hardware & Troubleshooting manual ({context_title}).\n"
                "Analyze this image or diagram carefully:\n"
                "1. If it's a UI / touchscreen screenshot: Extract all visible menu options, button labels, settings, port numbers, and exact error messages.\n"
                "2. If it's a hardware / pinout / cable diagram: Describe the pin connections, DIP switch settings, jumper positions, and cable routing.\n"
                "3. If it's a receipt or transaction sample: Extract the transaction breakdown and response codes.\n"
                "Provide a clear, detailed, technical transcription and summary so a field technician can search for and understand this visual content."
            )

            for model_name in ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.6-flash", "gemini-3.7-flash"]:
                try:
                    model = genai.GenerativeModel(model_name=model_name)
                    response = model.generate_content([prompt, pil_img], request_options={"timeout": 20.0})
                    if response and response.text:
                        return response.text.strip()
                except Exception as model_err:
                    err_str = str(model_err)
                    print(f"[VLM Extractor Warning] Gemini model {model_name} failed: {err_str}")
                    continue

        except Exception as e:
            print(f"[VLM Extractor Warning] Failed to describe image: {e}")

        return None
