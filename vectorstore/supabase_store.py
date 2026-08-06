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
        Executes hybrid search (vector similarity + keyword matching + score re-ranking) in Supabase.
        """
        # 1. Embed query text for vector search
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

        combined_matches: Dict[str, Dict[str, Any]] = {}

        # 2. Vector Similarity Search (Fetch top 15 candidates)
        try:
            res = self.client.rpc("match_documents", {
                "query_embedding": query_vec,
                "match_count": 15,
                "filter": filter_json
            }).execute()

            if res.data:
                for row in res.data:
                    c_id = row.get("id")
                    sim = float(row.get("similarity", 0.0))
                    combined_matches[c_id] = {
                        "id": c_id,
                        "text": row.get("text"),
                        "metadata": row.get("metadata", {}),
                        "score": sim,
                        "distance": 1.0 - sim
                    }
        except Exception as e:
            print(f"[Warning] Vector search error: {e}")

        # 3. Exact Keyword Search (Extract filenames, .ini, error numbers)
        keywords = re.findall(r'[A-Za-z0-9_\-\.]{3,}', query)
        important_terms = [kw.lower() for kw in keywords if len(kw) >= 4 or '.ini' in kw.lower() or kw.isdigit()]

        if important_terms:
            try:
                # Search Supabase text column for the exact phrase first
                exact_phrase = query.strip()
                kw_res = self.client.table(self.table_name).select("id, text, metadata").ilike("text", f"%{exact_phrase}%").limit(10).execute()
                
                # If exact phrase not found, fall back ONLY to highly specific technical terms
                # (e.g. error codes, filenames like .ini, or specific models like M400)
                if not kw_res.data and len(important_terms) > 0:
                     technical_terms = [t for t in important_terms if '.' in t or any(char.isdigit() for char in t) or t.isupper()]
                     if technical_terms:
                         term = technical_terms[0]
                         kw_res = self.client.table(self.table_name).select("id, text, metadata").ilike("text", f"%{term}%").limit(10).execute()

                if kw_res.data:
                    for row in kw_res.data:
                        c_id = row.get("id")
                        if c_id in combined_matches:
                            combined_matches[c_id]["score"] += 0.3  # Boost existing candidate
                        else:
                            combined_matches[c_id] = {
                                "id": c_id,
                                "text": row.get("text"),
                                "metadata": row.get("metadata", {}),
                                "score": 0.5,
                                "distance": 0.5
                            }
            except Exception as e:
                print(f"[Warning] Keyword search error: {e}")

        # 4. Rerank & Sort Candidates
        sorted_chunks = sorted(combined_matches.values(), key=lambda x: x["score"], reverse=True)
        return sorted_chunks[:top_k]

    def count(self) -> int:
        """Returns total document count in Supabase table."""
        try:
            res = self.client.table(self.table_name).select("id", count="exact").execute()
            return res.count or 0
        except Exception:
            return 0
