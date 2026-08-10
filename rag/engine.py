import re
import base64
import io
import json
from typing import Dict, Any, List, Optional
from vectorstore import VectorStoreManager
from llm import get_llm_provider, BaseLLMProvider
from .tavily_search import TavilySearcher

INTERNAL_KB_SYSTEM_PROMPT = """You are the AMPM Service technical support assistant for SMS by LOC point-of-sale systems.

You will be given retrieved internal documentation excerpts and a user's question.

Rules:
1. Answer using the provided internal documentation excerpts.
2. Synthesize information across all provided document excerpts to give clear, structured, step-by-step troubleshooting or configuration instructions.
3. Do NOT include inline citations or source references in the text body (do NOT write '(Source: ...)' or '(Source #...)' in paragraphs). Write clean text. The system automatically lists the source references at the bottom of the message.
4. Do NOT use markdown headers (such as ### or ####) or horizontal divider lines (such as --- or ***). Format section titles using simple bold text (e.g. **1. Section Title**).
5. If a specific sub-detail is not explicitly in the excerpts (e.g., exact field for partial authorization on a specific host), explain how the general configuration works based on the excerpts and clearly state what specific setting should be verified with support/manuals.
6. Do NOT output NOT_FOUND_IN_KB unless the excerpts are completely blank or 100% unrelated to any POS, register, bank, or payment topics.
7. Keep the tone practical, professional, and step-by-step, like an experienced POS field engineer speaking to another technician."""

WEB_FALLBACK_SYSTEM_PROMPT = """No internal documentation matched this question. You are now answering using web search results instead of company documentation.

Rules:
1. Base your answer only on the provided web search snippets.
2. Clearly state at the start of your answer that this information comes from external web sources, not verified AMPM/LOC documentation, and should be confirmed against official LOC or Verifone support channels before being applied — especially for anything involving payment processing or PCI-relevant settings.
3. Do NOT use markdown headers (such as ### or ####) or horizontal divider lines (such as --- or ***). Format section titles using simple bold text (e.g. **1. Section Title**).
4. If the web results appear to describe a different POS system, payment processor, or hardware model than what was asked about, say so explicitly rather than answering as if it matches.
5. Give clear, numbered steps where possible, citing which source each step comes from.
6. If the web results don't answer the question either, say so plainly and suggest contacting LOC support directly."""

QUERY_REWRITE_SYSTEM_PROMPT = """You rewrite technician support questions into a clean search query for a documentation retrieval system.

- Preserve exact error codes, model numbers, and product names exactly as written (e.g. "M400", "Mx915", "RBSLynk", "E-102", "Buypass").
- Remove conversational filler words like "Find in the documents only", "how can I", "please tell me".
- Output ONLY the rewritten query, nothing else."""

USER_PROMPT_TEMPLATE = """Documentation Context:
-------------------
{context_text}
-------------------

Conversation History:
{history_text}

Technician Question:
{question}
"""

class RAGEngine:
    """Core RAG retrieval, query expansion, and question-answering pipeline."""

    def __init__(self, vector_store: VectorStoreManager = None):
        self.vector_store = vector_store or VectorStoreManager()

    def _extract_text_from_images(self, images: list, api_key: str = None) -> Optional[str]:
        if not images:
            return None
        try:
            import google.generativeai as genai
            import config
            active_key = api_key or config.GEMINI_API_KEY
            if not active_key:
                return None

            genai.configure(api_key=active_key)

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

            for model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-flash-latest"]:
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

    def _rewrite_query_llm(self, query: str, provider_name: str, api_key: str = None) -> str:
        """Cleans and expands user queries to improve vector retrieval recall."""
        # Strip conversational filler locally to avoid burning API rate limits
        clean_q = re.sub(r'(?i)(find\s+in\s+the\s+documents\s+only|documents\s+only|internal\s+docs\s+only|you\s+can\s+also\s+search\s+on\s+the\s+web|search\s+web)', '', query).strip()
        return clean_q or query.strip()

    def _format_history(self, history: list) -> str:
        if not history:
            return "No previous conversation context."
        
        lines = []
        for turn in history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)

    def query(
        self,
        question: str,
        provider_name: str = None,
        top_k: int = 8,
        category: str = None,
        api_key: str = None,
        images: list = None,
        attachments: list = None,
        history: list = None,
        tavily_api_key: str = None
    ) -> Dict[str, Any]:
        """
        Executes intelligent RAG pipeline for a technician's question.
        Returns dictionary containing answer, citations, matches, provider_used, and is_web_fallback.
        """
        attached_text_blocks = []
        if attachments:
            for att in attachments:
                name = att.get("name", "Attached File")
                content = att.get("content", "")
                attached_text_blocks.append(f"\n[Technician Attached Reference File: {name}]\n{content}\n")

        full_question = question
        if attached_text_blocks:
            full_question += "\n" + "\n".join(attached_text_blocks)

        # Check if user explicitly requests web search or internal docs only
        web_search_requested = bool(re.search(r'(?i)(search\s+(on\s+the\s+|the\s+|on\s+)?web|search\s+online|google\s+it|web\s+search|look\s+on\s+(the\s+)?web|look\s+online)', full_question))
        documents_only_requested = bool(re.search(r'(?i)(documents\s+only|internal\s+docs|docs\s+only|in\s+the\s+documents)', full_question))

        image_extracted_text = None
        if images:
            image_extracted_text = self._extract_text_from_images(images, api_key=api_key)

        is_vague_question = len(full_question.strip().split()) <= 10
        if image_extracted_text:
            if is_vague_question:
                search_query = self._rewrite_query_llm(image_extracted_text, provider_name, api_key)
                full_question = f"{full_question}\n\n[Image Content]: {image_extracted_text}"
            else:
                combined = f"{full_question} {image_extracted_text}"
                search_query = self._rewrite_query_llm(combined, provider_name, api_key)
                full_question = f"{full_question}\n\n[Image Content]: {image_extracted_text}"
        else:
            search_query = self._rewrite_query_llm(full_question, provider_name, api_key)

        # Search vector store with enhanced multi-term matching
        matches = self.vector_store.search(query=search_query, top_k=top_k, category_filter=category)

        # Also search for key entity terms directly if sub-concepts exist
        key_entities = re.findall(r'(?i)\b(RBSLynk|Mx915|M400|Buypass|Fiserv|partial|tender|WIC|PayServer)\b', full_question)
        if key_entities:
            sub_matches = self.vector_store.search(query=" ".join(set(key_entities)), top_k=6, category_filter=category)
            seen_ids = set(m["id"] for m in matches)
            for sm in sub_matches:
                if sm["id"] not in seen_ids:
                    matches.append(sm)
                    seen_ids.add(sm["id"])

        # Filter matches by relevance score (discard irrelevant chunks below 0.40)
        valid_matches = [m for m in matches if m.get("score", 0) >= 0.40]

        history_text = self._format_history(history)
        provider: BaseLLMProvider = get_llm_provider(provider_name)
        
        def execute_web_fallback():
            print("[Info] Executing Web Fallback via Tavily...")
            tavily = TavilySearcher(api_key=tavily_api_key)
            web_results = tavily.search(search_query, top_k=5)
            
            if web_results["error"]:
                return {
                    "answer": f"No matching internal documentation was found for this query.\n\n[Web Search Failed]: {web_results['error']}",
                    "citations": [],
                    "matches": [],
                    "provider_used": provider.provider_name,
                    "is_web_fallback": True
                }
            
            context_blocks = tavily.format_results_as_context(web_results["results"])
            web_citations = []
            for r in web_results["results"]:
                web_citations.append({
                    "file_name": r.get("title", "Web Page"),
                    "page_number": "N/A",
                    "topic_title": "Web Search",
                    "location_ref": r.get("url", ""),
                    "category": "Web"
                })

            user_prompt = USER_PROMPT_TEMPLATE.format(context_text=context_blocks, history_text=history_text, question=full_question)
            fallback_answer = provider.generate_answer(system_prompt=WEB_FALLBACK_SYSTEM_PROMPT, user_prompt=user_prompt, api_key=api_key, images=images)
            
            return {
                "answer": fallback_answer,
                "citations": web_citations,
                "matches": [],
                "provider_used": provider.provider_name,
                "is_web_fallback": True
            }

        # If no valid relevant matches found in DB
        if not valid_matches:
            if web_search_requested and not documents_only_requested:
                return execute_web_fallback()
            else:
                return {
                    "answer": "No relevant internal documentation was found in the database for your query. (Web search was not executed as it was not explicitly requested in your prompt).",
                    "citations": [],
                    "matches": [],
                    "provider_used": provider.provider_name,
                    "is_web_fallback": False
                }

        # If user explicitly requested web search and internal match score is low (< 0.55), do web search
        max_score = max(m.get("score", 0) for m in valid_matches)
        if web_search_requested and not documents_only_requested and max_score < 0.55:
            return execute_web_fallback()

        context_blocks = []
        citations = []
        seen_citations = set()

        matches_sorted = sorted(valid_matches, key=lambda m: m.get("score", 0), reverse=True)

        for idx, match in enumerate(matches_sorted):
            meta = match.get("metadata", {})
            file_name = meta.get("file_name", "Unknown")
            page_num = meta.get("page_number", "?")
            topic_title = meta.get("topic_title", "").strip()
            cat = meta.get("category", "General")
            score = match.get("score", 0)

            if topic_title:
                location_ref = f"Topic: {topic_title}"
            else:
                location_ref = f"Page: {page_num}"

            context_blocks.append(
                f"--- [Source #{idx+1} | File: {file_name} | {location_ref} | Category: {cat}] ---\n"
                f"{match['text']}\n"
            )

            cite_key = f"{file_name}_{topic_title or page_num}"
            if cite_key not in seen_citations:
                seen_citations.add(cite_key)
                citations.append({
                    "file_name": file_name,
                    "page_number": page_num,
                    "topic_title": topic_title,
                    "location_ref": location_ref,
                    "category": cat,
                    "score": round(score, 3)
                })

        formatted_context = "\n".join(context_blocks)
        user_prompt = USER_PROMPT_TEMPLATE.format(context_text=formatted_context, history_text=history_text, question=full_question)

        answer = provider.generate_answer(system_prompt=INTERNAL_KB_SYSTEM_PROMPT, user_prompt=user_prompt, api_key=api_key, images=images)

        # Trigger web search only if user requested web search OR if answer says NOT_FOUND_IN_KB
        if "NOT_FOUND_IN_KB" in answer:
            if web_search_requested and not documents_only_requested:
                return execute_web_fallback()
            else:
                return {
                    "answer": "No relevant information was found in the internal documentation for your query.",
                    "citations": citations,
                    "matches": valid_matches,
                    "provider_used": provider.provider_name,
                    "is_web_fallback": False
                }

        return {
            "answer": answer,
            "citations": citations,
            "matches": valid_matches,
            "provider_used": provider.provider_name,
            "is_web_fallback": False
        }
