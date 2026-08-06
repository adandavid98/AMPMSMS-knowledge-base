import re
from typing import Dict, Any, List
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

        # 1. Expand search query for optimal retrieval
        search_query = self._expand_query(full_question)

        # 2. Retrieve top matching chunks (Hybrid Search)
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
        user_prompt = USER_PROMPT_TEMPLATE.format(context_text=formatted_context, question=question)

        # 4. Instantiate LLM Provider and generate answer
        provider: BaseLLMProvider = get_llm_provider(provider_name)
        answer = provider.generate_answer(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, api_key=api_key, images=images)

        return {
            "answer": answer,
            "citations": citations,
            "matches": matches,
            "provider_used": provider.provider_name
        }
