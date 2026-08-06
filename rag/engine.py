import re
import base64
import io
from typing import Dict, Any, List, Optional
from vectorstore import VectorStoreManager
from llm import get_llm_provider, BaseLLMProvider

SYSTEM_PROMPT = """You are an expert, highly intelligent technical support assistant for AMPM Service POS field technicians working on retail POS registers, payment terminals (Verifone, PinPads), and store servers.

STRICT INSTRUCTIONS:
1. Ground your answer ONLY in the provided Documentation Context below. Do NOT invent facts or procedures not supported by the context.
2. Adapt your response style intelligently based on the technician's query:
   - If they are reporting an ERROR or ISSUE: Provide clear, step-by-step troubleshooting instructions.
   - If they are asking for a SUMMARY, OVERVIEW, or CONFIGURATION DETAILS (e.g. .ini files, parameters): Provide a comprehensive, well-structured explanation using bullet points and clear sections.
3. For EVERY key fact, configuration setting, or step, include inline citations referencing the source document and page, formatted as: [Doc: <file_name>, Page: <page_number>].
4. If the documentation context contains ANY relevant information about the topic, present it thoroughly. Only state that information is missing if the context contains zero mention of the topic.
"""

USER_PROMPT_TEMPLATE = """Documentation Context:
-------------------
{context_text}
-------------------

Technician Question:
{question}
"""

class RAGEngine:
    """Core RAG retrieval, query expansion, and question-answering pipeline."""

    def __init__(self, vector_store: VectorStoreManager = None):
        self.vector_store = vector_store or VectorStoreManager()

    def _extract_text_from_images(self, images: list, api_key: str = None) -> Optional[str]:
        """
        Uses Gemini Vision to extract ALL text, error codes, and context from uploaded images.
        This extracted text is then used to search the documentation database accurately.
        Returns extracted text string, or None if extraction fails.
        """
        if not images:
            return None
        try:
            import google.generativeai as genai
            import config
            active_key = api_key or config.GEMINI_API_KEY
            if not active_key:
                return None

            genai.configure(api_key=active_key)

            # Build content list: OCR instruction + all images
            ocr_instruction = (
                "You are an OCR and technical context extractor. "
                "Read this image and extract ALL visible text exactly as it appears: "
                "error messages, error codes, window titles, dialog box content, menu labels, "
                "and any other text. Also describe what the screenshot is showing. "
                "Be thorough and literal — do not summarize. Output all extracted text."
            )
            contents = [ocr_instruction]

            for img_item in images:
                try:
                    from PIL import Image
                    if isinstance(img_item, str):
                        b64_data = img_item.split(",")[-1]
                    elif isinstance(img_item, dict) and "data" in img_item:
                        b64_data = img_item["data"].split(",")[-1]
                    else:
                        continue
                    img_bytes = base64.b64decode(b64_data)
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    contents.append(pil_img)
                except Exception as img_err:
                    print(f"[Warning] Could not decode image for OCR: {img_err}")
                    continue

            # Use Gemini Vision to extract text
            for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    model = genai.GenerativeModel(model_name=model_name)
                    response = model.generate_content(contents)
                    extracted = response.text.strip()
                    print(f"[Vision OCR] Extracted from image: {extracted[:200]}")
                    return extracted
                except Exception:
                    continue
        except Exception as e:
            print(f"[Warning] Vision extraction failed: {e}")
        return None

    def _expand_query(self, query: str) -> str:
        """Expands short or single-term user queries to improve retrieval recall."""
        q_clean = query.strip()
        lower_q = q_clean.lower()
        
        # Technical synonym mappings for common field tech terms
        synonyms = {
            "verifone": "verifone M400 pinpad terminal hardware WIC.ini payment",
            "setting.ini": "setting.ini WIC.ini SMS.ini configuration parameters server workstation",
            "settings.ini": "settings.ini WIC.ini SMS.ini configuration parameters server workstation",
            "buypass": "buypass fiserv payment host gateway error timeout 91",
            "buypassip": "buypass fiserv payment IP gateway host configuration",
            "m400": "verifone M400 pinpad payment terminal driver WIC.ini",
            "sms": "LOC Software SMS POS register master server configuration"
        }

        expanded_terms = []
        for key, expansion in synonyms.items():
            if key in lower_q:
                expanded_terms.append(expansion)

        if expanded_terms:
            return f"{q_clean} {' '.join(expanded_terms)}"
        return q_clean

    def query(
        self,
        question: str,
        provider_name: str = None,
        top_k: int = 6,
        category: str = None,
        api_key: str = None,
        images: list = None,
        attachments: list = None
    ) -> Dict[str, Any]:
        """
        Executes intelligent RAG pipeline for a technician's question.
        Returns dictionary containing answer, citations, matches, and provider_used.
        """
        # Format attachments if present
        attached_text_blocks = []
        if attachments:
            for att in attachments:
                name = att.get("name", "Attached File")
                content = att.get("content", "")
                attached_text_blocks.append(f"\n[Technician Attached Reference File: {name}]\n{content}\n")

        full_question = question
        if attached_text_blocks:
            full_question += "\n" + "\n".join(attached_text_blocks)

        # 1. Vision Pre-processing: extract text from images to use as search context
        image_extracted_text = None
        if images:
            image_extracted_text = self._extract_text_from_images(images, api_key=api_key)

        # 2. Build the best possible search query:
        #    - If image text was extracted, use it (it's the most specific and accurate)
        #    - Otherwise fall back to the user's typed question
        is_vague_question = len(full_question.strip().split()) <= 10  # Short/vague questions
        if image_extracted_text:
            if is_vague_question:
                # User typed something short like "What is this error?" — use image text as primary search query
                search_query = self._expand_query(image_extracted_text)
                # Append the user's typed question for final answer context
                full_question = f"{full_question}\n\n[Image Content]: {image_extracted_text}"
            else:
                # User typed a detailed question AND uploaded an image — combine both
                combined = f"{full_question} {image_extracted_text}"
                search_query = self._expand_query(combined)
                full_question = f"{full_question}\n\n[Image Content]: {image_extracted_text}"
        else:
            search_query = self._expand_query(full_question)

        # 3. Retrieve top matching chunks (Hybrid Search)
        matches = self.vector_store.search(query=search_query, top_k=top_k, category_filter=category)

        if not matches:
            return {
                "answer": "No relevant documentation found in the vector database. Please ingest documentation first.",
                "citations": [],
                "matches": [],
                "provider_used": provider_name or "N/A"
            }

        # 3. Format Context Blocks & Deduplicate Citations
        context_blocks = []
        citations = []
        seen_citations = set()

        for idx, match in enumerate(matches):
            meta = match.get("metadata", {})
            file_name = meta.get("file_name", "Unknown")
            page_num = meta.get("page_number", "?")
            cat = meta.get("category", "General")

            context_blocks.append(
                f"--- [Source #{idx+1} | File: {file_name} | Page: {page_num} | Category: {cat}] ---\n"
                f"{match['text']}\n"
            )

            cite_key = f"{file_name}_p{page_num}"
            if cite_key not in seen_citations:
                seen_citations.add(cite_key)
                citations.append({
                    "file_name": file_name,
                    "page_number": page_num,
                    "category": cat
                })

        formatted_context = "\n".join(context_blocks)
        # Use the enriched full_question (includes image context) for the final LLM prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(context_text=formatted_context, question=full_question)

        # 4. Instantiate LLM Provider and generate answer
        provider: BaseLLMProvider = get_llm_provider(provider_name)
        answer = provider.generate_answer(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, api_key=api_key, images=images)

        return {
            "answer": answer,
            "citations": citations,
            "matches": matches,
            "provider_used": provider.provider_name
        }
