import asyncio
import os
from dotenv import load_dotenv
from vectorstore.supabase_store import SupabaseVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

async def test_search():
    embedding_fn = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    store = SupabaseVectorStore(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        embedding_fn=embedding_fn
    )
    
    query = "how to setup dual monitor"
    print(f"Searching for: {query}")
    
    matches = store.search(query, top_k=6)
    
    print("\n--- RESULTS ---")
    for idx, match in enumerate(matches):
        meta = match.get("metadata", {})
        topic = meta.get("topic_title", "Unknown")
        file_name = meta.get("file_name", "Unknown")
        score = match.get("score", 0)
        print(f"{idx+1}. [{score:.4f}] {file_name} -> {topic}")
        # print(f"Text snippet: {match.get('text', '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_search())
