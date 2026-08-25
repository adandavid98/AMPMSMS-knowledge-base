import sys
import concurrent.futures
import config
from vectorstore.chroma_store import VectorStoreManager as ChromaStoreManager
from vectorstore.supabase_store import SupabaseVectorStore
from vectorstore.embeddings import GeminiEmbeddingFunction

def sync():
    """Fast multithreaded ONNX 384-dim cloud migration to Supabase (finishes in seconds)."""
    if not config.SUPABASE_URL or not (config.SUPABASE_KEY or config.SUPABASE_SERVICE_ROLE_KEY):
        print("[Error] SUPABASE_URL and SUPABASE_KEY must be set in your .env file before running sync.")
        sys.exit(1)

    print("=== AMPM Service POS Assistant - Fast Multithreaded ONNX Cloud Migration ===")

    # 1. Load local ChromaDB store
    print("\n[1/3] Reading text chunks from local ChromaDB...")
    chroma_store = ChromaStoreManager()
    local_count = chroma_store.count()
    print(f"      Found {local_count} total topic chunks.")

    if local_count == 0:
        print("[Warning] Local ChromaDB is empty! Nothing to migrate.")
        return

    records = chroma_store.collection.get(include=["documents", "metadatas"])
    ids = records["ids"]
    docs = records["documents"]
    metas = records["metadatas"]

    # 2. Connect to Supabase Cloud
    print("\n[2/3] Connecting to Supabase Cloud pgvector...")
    supabase_store = SupabaseVectorStore()
    print(f"      Connected to Supabase project: {config.SUPABASE_URL}")

    # 3. Multithreaded ONNX Upload (5 workers, 150 docs per batch)
    batch_size = 150
    batches = []
    for i in range(0, len(ids), batch_size):
        batches.append((
            ids[i:i + batch_size],
            docs[i:i + batch_size],
            metas[i:i + batch_size]
        ))

    print(f"\n[3/3] Uploading {len(ids)} chunks using 5 parallel workers...")

    def process_batch(batch_tuple):
        b_ids, b_docs, b_metas = batch_tuple
        embed_fn = GeminiEmbeddingFunction()
        b_embeddings = embed_fn(b_docs)

        records_to_upsert = []
        for idx in range(len(b_ids)):
            raw_emb = b_embeddings[idx]
            vec = raw_emb.tolist() if hasattr(raw_emb, "tolist") else [float(x) for x in raw_emb]
            records_to_upsert.append({
                "id": b_ids[idx],
                "text": b_docs[idx],
                "metadata": b_metas[idx],
                "embedding": vec
            })

        res = supabase_store.client.table(supabase_store.table_name).upsert(records_to_upsert).execute()
        return len(res.data) if res.data else 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_batch, b) for b in batches]
        total_uploaded = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                uploaded_count = future.result()
                total_uploaded += uploaded_count
                pct = (total_uploaded / len(ids)) * 100
                print(f"      Progress: {total_uploaded}/{len(ids)} ({pct:.1f}%) uploaded...")
            except Exception as e:
                print(f"      [Warning] Batch upload error: {e}")

    print("\n=======================================================")
    print("Migration Complete!")
    print(f"Supabase total documents count: {supabase_store.count()}")
    print("=======================================================")

if __name__ == "__main__":
    sync()
