import re
from typing import List, Dict, Any
from supabase import create_client, Client
import config
from .embeddings import GeminiEmbeddingFunction

class SupabaseVectorStore:
    """Manages cloud vector database operations in Supabase pgvector with hybrid search."""

    def __init__(self, url: str = None, key: str = None, table_name: str = "documents"):
        self.url = url or config.SUPABASE_URL
        self.key = key or config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_KEY
        self.table_name = table_name
        self.embedding_fn = GeminiEmbeddingFunction()

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured for Supabase cloud vector store.")

        self.client: Client = create_client(self.url, self.key)

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Generates embeddings and upserts document chunks into Supabase pgvector.
        Returns count of added chunks.
        """
        if not chunks:
            return 0

        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_fn(texts)

        records = []
        for idx, chunk in enumerate(chunks):
            raw_emb = embeddings[idx]
            if hasattr(raw_emb, "tolist"):
                vec = raw_emb.tolist()
            else:
                vec = [float(x) for x in raw_emb]

            records.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "embedding": vec
            })

        batch_size = 50
        total_upserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            res = self.client.table(self.table_name).upsert(batch).execute()
            if res.data:
                total_upserted += len(res.data)

        return total_upserted

    def search(self, query: str, top_k: int = 6, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Executes consolidated hybrid search (vector similarity + keyword matching)
        in a single database round-trip via match_documents_hybrid RPC.
        """
        # 1. Fast Google native query embedding (~50-100ms)
        raw_query_emb = self.embedding_fn.embed_query(query)
        if isinstance(raw_query_emb, list) and len(raw_query_emb) > 0:
            query_vec = raw_query_emb[0]
        else:
            query_vec = raw_query_emb

        if hasattr(query_vec, "tolist"):
            query_vec = query_vec.tolist()
        else:
            query_vec = [float(x) for x in query_vec]

        filter_json = {}
        if category_filter and category_filter not in ["General", "All Documentation", ""]:
            filter_json = {"category": category_filter}

        matches: List[Dict[str, Any]] = []

        # 2. Consolidated Hybrid Search in 1 DB Round-Trip
        try:
            res = self.client.rpc("match_documents_hybrid", {
                "query_embedding": query_vec,
                "query_text": query,
                "match_count": max(top_k * 2, 10),
                "filter": filter_json
            }).execute()

            if res.data:
                for row in res.data:
                    sim = float(row.get("similarity", 0.0))
                    matches.append({
                        "id": row.get("id"),
                        "text": row.get("text"),
                        "metadata": row.get("metadata", {}),
                        "score": sim,
                        "distance": max(0.0, 1.0 - sim)
                    })
        except Exception as e:
            print(f"[Supabase Warning] match_documents_hybrid RPC failed ({e}). Falling back to match_documents.")
            try:
                fallback_res = self.client.rpc("match_documents", {
                    "query_embedding": query_vec,
                    "match_count": top_k,
                    "filter": filter_json
                }).execute()
                if fallback_res.data:
                    for row in fallback_res.data:
                        sim = float(row.get("similarity", 0.0))
                        matches.append({
                            "id": row.get("id"),
                            "text": row.get("text"),
                            "metadata": row.get("metadata", {}),
                            "score": sim,
                            "distance": max(0.0, 1.0 - sim)
                        })
            except Exception as fb_err:
                print(f"[Supabase Error] Fallback vector search also failed: {fb_err}")

        # 3. Sort Candidates and return top_k
        sorted_chunks = sorted(matches, key=lambda x: x["score"], reverse=True)
        return sorted_chunks[:top_k]


    def count(self) -> int:
        """Returns total document count in Supabase table."""
        try:
            # Adding limit(1) prevents downloading all IDs while still getting the exact count
            res = self.client.table(self.table_name).select("id", count="exact").limit(1).execute()
            # In the Supabase python client, count is an attribute on the response object
            return res.count if res.count is not None else 0
        except Exception as e:
            print(f"[Warning] Error getting document count: {e}")
            return 0
