from typing import List, Dict, Any
from supabase import create_client, Client
import config
from .embeddings import GeminiEmbeddingFunction

class SupabaseVectorStore:
    """Manages cloud vector database operations in Supabase pgvector."""

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

        # Generate embeddings for text batch
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

        # Upsert records in batches of 50
        batch_size = 50
        total_upserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            res = self.client.table(self.table_name).upsert(batch).execute()
            if res.data:
                total_upserted += len(res.data)

        return total_upserted

    def search(self, query: str, top_k: int = 5, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Executes RPC cosine similarity search in Supabase pgvector.
        """
        # Embed query text
        raw_query_emb = self.embedding_fn.embed_query(query)
        if isinstance(raw_query_emb, list) and len(raw_query_emb) > 0:
            query_vec = raw_query_emb[0]
        else:
            query_vec = raw_query_emb

        # Convert numpy array to float list for JSON serialization
        if hasattr(query_vec, "tolist"):
            query_vec = query_vec.tolist()
        else:
            query_vec = [float(x) for x in query_vec]

        filter_json = {}
        if category_filter and category_filter != "General":
            filter_json = {"category": category_filter}

        # Invoke match_documents RPC function
        try:
            res = self.client.rpc("match_documents", {
                "query_embedding": query_vec,
                "match_count": top_k,
                "filter": filter_json
            }).execute()

            matches = []
            if res.data:
                for row in res.data:
                    matches.append({
                        "id": row.get("id"),
                        "text": row.get("text"),
                        "metadata": row.get("metadata", {}),
                        "distance": 1.0 - float(row.get("similarity", 0.0))
                    })
            return matches
        except Exception as e:
            print(f"[Error] Supabase RPC match_documents search failed: {e}")
            return []

    def count(self) -> int:
        """Returns total document count in Supabase table."""
        try:
            res = self.client.table(self.table_name).select("id", count="exact").execute()
            return res.count or 0
        except Exception:
            return 0
