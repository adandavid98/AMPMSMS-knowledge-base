from typing import Dict, Any, List
from vectorstore import VectorStoreManager
from llm import get_llm_provider, BaseLLMProvider

SYSTEM_PROMPT = """You are an expert technical support assistant for AMPM Service POS field technicians working on retail POS registers, payment terminals, and store servers.

STRICT INSTRUCTIONS:
1. Answer the technician's question ONLY using the provided Documentation Context below.
2. For EVERY step, fix, or fact you state, include an exact citation inline referencing the source document and page number, in the format: [Doc: <file_name>, Page: <page_number>].
3. Summarize or explain whatever information IS present in the context regarding the user's query. Only state that information is insufficient if the provided context contains zero relevant details about the user's question. Do NOT guess or hallucinate solutions outside the provided context.
4. Format your answer clearly with markdown bullet points or step-by-step technical instructions.
"""

USER_PROMPT_TEMPLATE = """Documentation Context:
-------------------
{context_text}
-------------------

Technician Question:
{question}
"""

class RAGEngine:
    """Core RAG retrieval and question-answering pipeline."""

    def __init__(self, vector_store: VectorStoreManager = None):
        self.vector_store = vector_store or VectorStoreManager()

    def query(
        self,
        question: str,
        provider_name: str = None,
        top_k: int = 5,
        category: str = None,
        api_key: str = None,
        images: list = None,
        attachments: list = None
    ) -> Dict[str, Any]:
        """
        Executes RAG pipeline for a technician's question.
        Returns dictionary containing answer, citations, matches, and provider_used.
        """
        # Format attachments (reference text / logs / snippets)
        attached_text_blocks = []
        if attachments:
            for att in attachments:
                name = att.get("name", "Attached File")
                content = att.get("content", "")
                attached_text_blocks.append(f"\n[Technician Attached Reference File: {name}]\n{content}\n")

        full_question = question
        if attached_text_blocks:
            full_question += "\n" + "\n".join(attached_text_blocks)

        # 1. Retrieve top matching chunks from ChromaDB
        matches = self.vector_store.search(query=full_question, top_k=top_k, category_filter=category)

        if not matches:
            return {
                "answer": "No relevant documentation found in the vector database. Please ingest documentation first.",
                "citations": [],
                "matches": [],
                "provider_used": provider_name or "N/A"
            }

        # 2. Format Context Blocks
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

        # 3. Instantiate LLM Provider and generate answer
        provider: BaseLLMProvider = get_llm_provider(provider_name)
        answer = provider.generate_answer(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, api_key=api_key, images=images)

        return {
            "answer": answer,
            "citations": citations,
            "matches": matches,
            "provider_used": provider.provider_name
        }
