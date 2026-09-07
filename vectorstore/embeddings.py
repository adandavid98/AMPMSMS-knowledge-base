"""
High-performance native embedding engine using Google Gemini API (models/text-embedding-004).
Generates 768-dimensional semantic embeddings in ~50-100ms with zero heavy local dependencies.
100% compliant with Vercel's 250MB serverless bundle limit.
"""
import os
import time
from typing import List, Union
import google.generativeai as genai
import config

_DIM = 768

class GeminiEmbeddingFunction:
    """
    Native Google Gemini Embedding Function (models/text-embedding-004, 768-dim).
    Supports single query embedding and high-throughput batch document ingestion.
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = model_name or config.GEMINI_EMBEDDING_MODEL or "models/text-embedding-004"
        if not self.model_name.startswith("models/"):
            self.model_name = f"models/{self.model_name}"

    def name(self) -> str:
        return "gemini_embedding_function"

    def _get_active_keys(self, custom_key: str = None) -> List[str]:
        raw_key = custom_key or self.api_key or config.GEMINI_API_KEY
        if not raw_key:
            return []
        return [k.strip() for k in raw_key.split(",") if k.strip()]

    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        """
        Embeds a list of document chunks for storage using task_type='retrieval_document'.
        Batches requests into groups of up to 100 chunks.
        """
        if not input:
            return []
        if isinstance(input, str):
            input = [input]

        texts = list(input)
        keys = self._get_active_keys()

        if not keys:
            print("[Warning] GEMINI_API_KEY not found. Cannot generate embeddings.")
            return [[0.0] * _DIM for _ in texts]

        all_embeddings: List[List[float]] = []
        batch_size = 100  # Google embed_content limit per batch

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_success = False
            last_err = None

            max_retries = 3
            for attempt in range(max_retries):
                for key in keys:
                    try:
                        genai.configure(api_key=key)
                        res = genai.embed_content(
                            model=self.model_name,
                            content=batch,
                            task_type="retrieval_document",
                            output_dimensionality=_DIM
                        )

                        embs = res.get("embedding", [])
                        if embs:
                            if isinstance(embs[0], list):
                                all_embeddings.extend(embs)
                            else:
                                all_embeddings.append(embs)
                            batch_success = True
                            break
                    except Exception as e:
                        last_err = e
                        if "429" in str(e):
                            wait_s = 10 * (attempt + 1)
                            print(f"[RateLimit 429] Pacing API quota. Retrying batch in {wait_s}s...")
                            time.sleep(wait_s)
                            break
                        continue

                if batch_success:
                    break

            if not batch_success:
                print(f"[Error] Failed to embed batch of {len(batch)} documents after {max_retries} retries: {last_err}")
                all_embeddings.extend([[0.0] * _DIM for _ in batch])


        return all_embeddings

    def embed_query(self, input=None, *args, **kwargs) -> List[List[float]]:
        """
        Embeds a search query using task_type='retrieval_query' for maximum semantic retrieval accuracy.
        """
        query_text = input
        if query_text is None and args:
            query_text = args[0]
        if query_text is None:
            query_text = kwargs.get("text", "")
        if isinstance(query_text, list):
            query_text = query_text[0] if query_text else ""

        query_text = str(query_text).strip()
        if not query_text:
            return [[0.0] * _DIM]

        custom_key = kwargs.get("api_key")
        keys = self._get_active_keys(custom_key)
        if not keys:
            print("[Warning] GEMINI_API_KEY not found. Cannot embed query.")
            return [[0.0] * _DIM]

        for key in keys:
            try:
                genai.configure(api_key=key)
                res = genai.embed_content(
                    model=self.model_name,
                    content=query_text,
                    task_type="retrieval_query",
                    output_dimensionality=_DIM
                )

                emb = res.get("embedding", [])
                if emb:
                    if isinstance(emb[0], list):
                        return emb
                    return [emb]
            except Exception as e:
                print(f"[Warning] Query embedding attempt failed: {e}")
                continue

        return [[0.0] * _DIM]

