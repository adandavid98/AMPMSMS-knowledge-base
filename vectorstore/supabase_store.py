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

        # 2. Vector Similarity Search (Fetch top 20 candidates, filter by min threshold)
        MIN_SIMILARITY = 0.35  # Discard chunks with very low semantic relevance
        try:
            res = self.client.rpc("match_documents", {
                "query_embedding": query_vec,
                "match_count": 20,
                "filter": filter_json
            }).execute()

            if res.data:
                for row in res.data:
                    c_id = row.get("id")
                    sim = float(row.get("similarity", 0.0))
                    if sim < MIN_SIMILARITY:
                        print(f"[Search] Dropped low-relevance chunk (score={sim:.2f}): {row.get('metadata', {}).get('topic_title', c_id)}")
                        continue
                    combined_matches[c_id] = {
                        "id": c_id,
                        "text": row.get("text"),
                        "metadata": row.get("metadata", {}),
                        "score": sim,
                        "distance": 1.0 - sim
                    }
        except Exception as e:
            print(f"[Warning] Vector search error: {e}")

        # 3. Enhanced Multi-Term Keyword & Topic Title Search
        raw_words = re.findall(r'[A-Za-z0-9_\-\.]{3,}', query)
        stop_words = {"find", "documents", "only", "how", "can", "setup", "set", "using", "with", "from", "the", "for", "and", "that", "this", "what", "which", "your", "are"}
        key_terms = sorted([w for w in raw_words if w.lower() not in stop_words and len(w) >= 3], key=len, reverse=True)

        try:
            # Step A: Topic Title N-Gram Matching (Extremely high relevance for topic titles)
            words_filtered = [w for w in raw_words if w.lower() not in stop_words]
            for n in range(min(len(words_filtered), 4), 1, -1):
                for i in range(len(words_filtered) - n + 1):
                    ngram = " ".join(words_filtered[i:i+n])
                    title_res = self.client.table(self.table_name).select("id, text, metadata").ilike("metadata->>topic_title", f"%{ngram}%").limit(10).execute()
                    if title_res.data:
                        for row in title_res.data:
                            c_id = row["id"]
                            combined_matches[c_id] = {
                                "id": c_id,
                                "text": row.get("text"),
                                "metadata": row.get("metadata", {}),
                                "score": 0.98,
                                "distance": 0.02
                            }

            # Step B: Keyword Hits in Text & Metadata
            keyword_hits = {}
            for term in key_terms[:8]:
                kw_res = self.client.table(self.table_name).select("id").ilike("text", f"%{term}%").limit(150).execute()
                if kw_res.data:
                    for row in kw_res.data:
                        c_id = row.get("id")
                        keyword_hits[c_id] = keyword_hits.get(c_id, 0) + 1

            best_c_ids = [c_id for c_id, count in keyword_hits.items() if count >= 2 or c_id in combined_matches]
            if best_c_ids:
                best_res = self.client.table(self.table_name).select("id, text, metadata").in_("id", best_c_ids).execute()
                if best_res.data:
                    for row in best_res.data:
                        c_id = row["id"]
                        count = keyword_hits.get(c_id, 0)
                        
                        if c_id in combined_matches:
                            combined_matches[c_id]["score"] += (count * 0.10)
                        else:
                            new_score = 0.50 + (count * 0.10)
                            combined_matches[c_id] = {
                                "id": c_id,
                                "text": row.get("text"),
                                "metadata": row.get("metadata", {}),
                                "score": min(new_score, 0.90),
                                "distance": 1.0 - min(new_score, 0.90)
                            }
                        
        except Exception as e:
            print(f"[Warning] Keyword / Title search error: {e}")

        # 4. Rerank & Sort Candidates
        sorted_chunks = sorted(combined_matches.values(), key=lambda x: x["score"], reverse=True)
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
