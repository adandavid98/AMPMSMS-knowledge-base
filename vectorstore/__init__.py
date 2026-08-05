import config
from .embeddings import GeminiEmbeddingFunction

def VectorStoreManager(*args, **kwargs):
    """
    Dual-mode Vector Store Factory.
    - If SUPABASE_URL and key are configured, returns a SupabaseVectorStore instance.
    - Otherwise, returns a local ChromaDB VectorStoreManager instance.
    """
    use_supabase = bool(config.SUPABASE_URL and (config.SUPABASE_KEY or config.SUPABASE_SERVICE_ROLE_KEY))

    if use_supabase:
        try:
            from .supabase_store import SupabaseVectorStore
            print("[Info] Connecting to Cloud Vector Store: Supabase pgvector")
            return SupabaseVectorStore()
        except Exception as e:
            print(f"[Warning] Failed to initialize Supabase vector store ({e}). Falling back to local ChromaDB.")

    from .chroma_store import VectorStoreManager as ChromaStoreManager
    return ChromaStoreManager(*args, **kwargs)

__all__ = ["GeminiEmbeddingFunction", "VectorStoreManager"]
