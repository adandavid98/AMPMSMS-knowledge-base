import re
import base64
import io
import json
from typing import Dict, Any, List, Optional
from vectorstore import VectorStoreManager
from llm import get_llm_provider, BaseLLMProvider
from .tavily_search import TavilySearcher
from .hybrid_retriever import HybridRetriever
from ingestion.vlm_extractor import VLMExtractor
from telemetry import telemetry
import config

INTERNAL_KB_SYSTEM_PROMPT = """You are the AMPM Service technical support assistant for SMS by LOC point-of-sale systems.

You will be given retrieved internal documentation excerpts (including structured tables, category groupings, and technical definitions) and a user's question. If the user attaches files or images, their extracted text will be appended to the question.

Rules:
1. Answer using the provided internal documentation excerpts AND any [Technician Attached Reference File] or [Image Content] provided in the question. Treat attached technical documents as highly authoritative.
2. Ground your answer in the specific details found in the excerpts:
   - When asked about database tables, system components, or categories, provide the EXACT table names (e.g., ALT_TAB, FCT_TAB, REC_BAT), category groups (e.g., Item tables, Auxiliary tables, System tables, Customer tables, Batch tables), and descriptions directly as documented in the manual.
   - When asked for troubleshooting or setup, provide clear, numbered, step-by-step instructions.
3. Do NOT replace specific documented tables, parameters, or categories with vague generalized overviews when exact data is in the excerpts.
4. Do NOT include inline citations or source references in the text body (do NOT write '(Source: ...)' or '(Source #...)' in paragraphs). Write clean text. The system automatically lists the source references at the bottom of the message.
5. Do NOT use markdown headers (such as ### or ####) or horizontal divider lines (such as --- or ***). Format section titles using simple bold text (e.g. **1. Section Title**).
6. If a specific sub-detail is not explicitly in the excerpts or attachments, explain how the general configuration works based on them and clearly state what specific setting should be verified with support.
7. Do NOT output NOT_FOUND_IN_KB unless both the retrieved excerpts AND the attached contents are completely blank or 100% unrelated to any POS, register, bank, or payment topics.
8. Keep the tone practical, professional, and precise, like an experienced POS field engineer speaking to another technician."""

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
    """Core RAG retrieval, query expansion, and question-answering pipeline with Hybrid Search & Telemetry."""

    def __init__(self, vector_store: VectorStoreManager = None):
        self.vector_store = vector_store or VectorStoreManager()
        self.hybrid_retriever = HybridRetriever(vector_store=self.vector_store)
        self.vlm_extractor = VLMExtractor()

    def _extract_text_from_images(self, images: list, api_key: str = None) -> Optional[str]:
        if not images:
            return None
        try:
            for img_item in images:
                desc = self.vlm_extractor.describe_image(img_item, context_title="Technician Uploaded Photo")
                if desc:
                    return desc
        except Exception as e:
            print(f"[Warning] Vision extraction failed: {e}")
        return None

    def _clean_query_text(self, query: str) -> str:
        """Removes conversational fluff and extracts clean search intent."""
        clean = re.sub(
            r'(?i)(find\s+in\s+the\s+documents\s+only|documents\s+only|internal\s+docs\s+only|you\s+can\s+also\s+search\s+on\s+the\s+web|search\s+web|search\s+online|please\s+tell\s+me|can\s+you\s+tell\s+me|how\s+do\s+i|how\s+can\s+i|what\s+is\s+the|is\s+there\s+a|where\s+is|are\s+there)',
            ' ',
            query
        )
        clean = re.sub(r'[\?\"\']', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _sanitize_llm_rewrite(self, text: str) -> str:
        """Strips chat preambles from LLM outputs like 'Here is the rewritten query:...'"""
        if not text:
            return ""
        text = re.sub(r'(?i)^(here\s+(is|are)\s+the\s+(rewritten\s+)?(query|keywords|search\s+terms?)[:\s\-]*|rewritten\s+query[:\s\-]*|search\s+query[:\s\-]*|keywords?[:\s\-]*)', '', text.strip())
        text = text.replace('"', '').replace('`', '').strip()
        return text

    def _rewrite_query_llm(self, query: str, provider_name: str = None, api_key: str = None) -> str:
        """Cleans and expands user queries to improve retrieval recall reliably."""
        clean_q = self._clean_query_text(query)
        if not clean_q:
            return query.strip()

        # If query already contains specific technical POS entities or error codes, skip LLM rewrite to eliminate latency
        has_pos_entity = bool(re.search(r'(?i)\b(RBSLynk|Mx915|M400|Buypass|Fiserv|partial|tender|WIC|PayServer|rtm|sqr|xf|reportbuilder|storeman|eod|bod|pinpad|invoicing|pricebook|fct_tab|alt_tab|rec_bat|loc|ssf|error\s*\d+|code\s*\d+)\b', clean_q))
        if has_pos_entity:
            return clean_q

        # Decouple rewrite from chosen LLM: prefer Gemini if available to ensure robust search for all providers
        rewrite_provider = "gemini" if (config.GEMINI_API_KEY or (provider_name == "gemini" and api_key)) else provider_name
        rewrite_key = api_key if rewrite_provider == provider_name else config.GEMINI_API_KEY

        try:
            provider = get_llm_provider(rewrite_provider)
            user_prompt = f"Original Query: {clean_q}\n\nRewrite this to extract only the most important technical keywords and file names for a database search."
            rewritten = provider.generate_answer(
                system_prompt=QUERY_REWRITE_SYSTEM_PROMPT, 
                user_prompt=user_prompt, 
                api_key=rewrite_key
            )
            cleaned_rewritten = self._sanitize_llm_rewrite(rewritten)
            if cleaned_rewritten and not cleaned_rewritten.isspace() and len(cleaned_rewritten.split()) <= 20:
                # Combine original clean query with rewritten keywords to maximize recall
                return f"{clean_q} {cleaned_rewritten}"
        except Exception as e:
            print(f"[Warning] LLM query rewrite failed: {e}. Using regex fallback.")

        return clean_q

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
        tavily_api_key: str = None,
        user_email: str = None
    ) -> Dict[str, Any]:
        """
        Executes intelligent RAG pipeline with Hybrid Retrieval, VLM comprehension, and Langfuse tracing.
        """
        # Start Langfuse Trace
        trace = telemetry.create_trace(
            name="rag_technician_query",
            user_id=user_email or "anonymous_tech",
            metadata={"category": category, "provider": provider_name}
        )

        attached_text_blocks = []
        if attachments:
            for att in attachments:
                name = att.get("name", "Attached File")
                content = att.get("content", "")
                attached_text_blocks.append(f"\n[Technician Attached Reference File: {name}]\n{content}\n")

        full_question = question
        if attached_text_blocks:
            full_question += "\n" + "\n".join(attached_text_blocks)

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

        # Ensure key exact POS, hardware, and file/folder entity terms are part of the primary search query
        key_entities = re.findall(
            r'(?i)\b(RBSLynk|Mx915|M400|Buypass|Fiserv|partial|tender|WIC|PayServer|rtm|sqr|xf|reportbuilder|storeman|eod|bod|pinpad|invoicing|pricebook|fct_tab|alt_tab|rec_bat|loc|ssf)\b',
            full_question
        )
        if key_entities:
            search_query = f"{search_query} {' '.join(set(key_entities))}"

        # Retrieval Span (Single unified fast search pass)
        retrieval_span = trace.span(name="retrieval_hybrid")
        if config.USE_HYBRID_SEARCH:
            matches = self.hybrid_retriever.search(query=search_query, top_k=top_k, category=category)
        else:
            matches = self.vector_store.search(query=search_query, top_k=top_k, category_filter=category)
        retrieval_span.end()

        # Score threshold filtering
        valid_matches = [m for m in matches if m.get("score", 0.5) >= 0.35]

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
                    "is_web_fallback": True,
                    "trace_id": trace.id
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
                "is_web_fallback": True,
                "trace_id": trace.id
            }

        # If no valid matches found in DB
        if not valid_matches:
            if web_search_requested and not documents_only_requested:
                return execute_web_fallback()
            else:
                return {
                    "answer": "No relevant internal documentation was found in the database for your query. (Web search was not executed as it was not explicitly requested in your prompt).",
                    "citations": [],
                    "matches": [],
                    "provider_used": provider.provider_name,
                    "is_web_fallback": False,
                    "trace_id": trace.id
                }

        max_score = max(m.get("score", 0.5) for m in valid_matches)
        if web_search_requested and not documents_only_requested and max_score < 0.55:
            return execute_web_fallback()

        context_blocks = []
        citations = []
        seen_citations = set()

        matches_sorted = sorted(valid_matches, key=lambda m: m.get("score", 0.5), reverse=True)

        for idx, match in enumerate(matches_sorted):
            meta = match.get("metadata", {})
            file_name = meta.get("file_name", "Unknown")
            page_num = meta.get("page_number", "?")
            topic_title = meta.get("topic_title", "").strip()
            cat = meta.get("category", "General")
            score = match.get("score", 0.5)

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

        # Generation Span
        gen_span = trace.span(name="llm_reasoning_generation")
        answer = provider.generate_answer(system_prompt=INTERNAL_KB_SYSTEM_PROMPT, user_prompt=user_prompt, api_key=api_key, images=images)
        gen_span.end()

        if "NOT_FOUND_IN_KB" in answer:
            if web_search_requested and not documents_only_requested:
                return execute_web_fallback()
            else:
                return {
                    "answer": "No relevant information was found in the internal documentation for your query.",
                    "citations": citations,
                    "matches": valid_matches,
                    "provider_used": provider.provider_name,
                    "is_web_fallback": False,
                    "trace_id": trace.id
                }

        return {
            "answer": answer,
            "citations": citations,
            "matches": valid_matches,
            "provider_used": provider.provider_name,
            "is_web_fallback": False,
            "trace_id": trace.id
        }
