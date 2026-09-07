import sys
import time
import concurrent.futures
import config
from vectorstore.supabase_store import SupabaseVectorStore
from vectorstore.embeddings import GeminiEmbeddingFunction

def sync():
    """Fast Google Native 768-dim cloud migration to Supabase."""
    key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_KEY
    if not config.SUPABASE_URL or not key:
        print("[Error] SUPABASE_URL and SUPABASE_KEY/SERVICE_ROLE_KEY must be set in your .env file before running sync.")
        sys.exit(1)

    print("=== AMPM Service POS Assistant - Fast Google 768-dim Cloud Migration ===")

    supabase_store = SupabaseVectorStore()
    client = supabase_store.client

    # 1. Check if documents_backup_384 exists in Supabase
    backup_count = 0
    try:
        b_res = client.table("documents_backup_384").select("id", count="exact").limit(1).execute()
        backup_count = b_res.count or 0
    except Exception:
        backup_count = 0

    embed_fn = GeminiEmbeddingFunction()

    if backup_count > 0:
        print(f"\n[1/2] Found {backup_count} document chunks in Supabase backup table (documents_backup_384).")
        print(f"[2/2] Generating 768-dim Google embeddings and populating 'documents' table...")

        page_size = 1000
        total_uploaded = 0
        t0 = time.time()

        for start_idx in range(0, backup_count, page_size):
            end_idx = min(start_idx + page_size - 1, backup_count - 1)
            fetch_res = client.table("documents_backup_384").select("id, text, metadata").range(start_idx, end_idx).execute()
            rows = fetch_res.data or []
            if not rows:
                break

            # Fast batch embedding (80 chunks per request on Paid Tier)
            batch_size = 80
            for b_i in range(0, len(rows), batch_size):
                b_slice = rows[b_i:b_i + batch_size]
                b_ids = [r["id"] for r in b_slice]

                # Check which chunks already exist in 'documents'
                try:
                    chk_res = client.table(supabase_store.table_name).select("id").in_("id", b_ids).execute()
                    already_done = set(r["id"] for r in (chk_res.data or []))
                except Exception:
                    already_done = set()

                to_process = [r for r in b_slice if r["id"] not in already_done]

                if to_process:
                    texts = [r["text"] for r in to_process]
                    embs = embed_fn(texts)

                    records = []
                    for idx, r in enumerate(to_process):
                        records.append({
                            "id": r["id"],
                            "text": r["text"],
                            "metadata": r.get("metadata", {}),
                            "embedding": embs[idx]
                        })

                    client.table(supabase_store.table_name).upsert(records).execute()
                    time.sleep(0.1)  # Minimal micro-pause on paid tier

                total_uploaded += len(b_slice)
                pct = (total_uploaded / backup_count) * 100
                elapsed = time.time() - t0
                print(f"      Progress: {total_uploaded}/{backup_count} ({pct:.1f}%) processed in {elapsed:.1f}s...")



    else:
        # Fallback to local ChromaDB
        print("\n[1/2] Reading text chunks from local ChromaDB...")
        from vectorstore.chroma_store import VectorStoreManager as ChromaStoreManager
        chroma_store = ChromaStoreManager()
        local_count = chroma_store.count()
        print(f"      Found {local_count} total topic chunks.")

        if local_count == 0:
            print("[Warning] No documents found in backup or local ChromaDB to migrate.")
            return

        records = chroma_store.collection.get(include=["documents", "metadatas"])
        ids = records["ids"]
        docs = records["documents"]
        metas = records["metadatas"]

        print(f"\n[2/2] Uploading {len(ids)} chunks with 768-dim Google embeddings...")
        batch_size = 80
        total_uploaded = 0
        for i in range(0, len(ids), batch_size):
            b_ids = ids[i:i + batch_size]
            b_docs = docs[i:i + batch_size]
            b_metas = metas[i:i + batch_size]
            b_embeddings = embed_fn(b_docs)

            upsert_records = []
            for idx in range(len(b_ids)):
                upsert_records.append({
                    "id": b_ids[idx],
                    "text": b_docs[idx],
                    "metadata": b_metas[idx],
                    "embedding": b_embeddings[idx]
                })

            client.table(supabase_store.table_name).upsert(upsert_records).execute()
            total_uploaded += len(upsert_records)
            pct = (total_uploaded / len(ids)) * 100
            print(f"      Progress: {total_uploaded}/{len(ids)} ({pct:.1f}%) uploaded...")

    print("\n=======================================================")
    print("Migration Complete!")
    print(f"Supabase total documents count: {supabase_store.count()}")
    print("=======================================================")


if __name__ == "__main__":
    sync()
