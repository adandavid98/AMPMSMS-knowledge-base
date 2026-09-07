import time
from dotenv import load_dotenv
from vectorstore import VectorStoreManager

load_dotenv()

def run_test():
    store = VectorStoreManager()
    print(f"Total live chunks in store: {store.count()}")
    
    queries = [
        "M400 cash back error",
        "Buypass host timeout error 91",
        "Operator table maintenance"
    ]
    
    for q in queries:
        t0 = time.time()
        results = store.search(q, top_k=3)
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        print(f"\n--- Query: '{q}' (Retrieved in {elapsed_ms} ms) ---")
        for idx, r in enumerate(results):
            meta = r.get("metadata", {})
            file_name = meta.get("file_name", "Unknown")
            topic = meta.get("topic_title", "N/A")
            score = r.get("score", 0)
            print(f"  {idx+1}. [{score:.3f}] {file_name} -> {topic}")

if __name__ == "__main__":
    run_test()

