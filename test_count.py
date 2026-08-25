import asyncio
import os
from dotenv import load_dotenv
from vectorstore.supabase_store import SupabaseVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

async def test_count():
    store = SupabaseVectorStore(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        embedding_fn=None # Don't need embeddings to count
    )
    
    try:
        res = store.client.table(store.table_name).select("id", count="exact").limit(1).execute()
        print(f"Res: {res}")
        print(f"Count: {res.count}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_count())
