import os
from dotenv import load_dotenv
from vectorstore import VectorStoreManager

load_dotenv()

def run_test():
    store = VectorStoreManager()
    print(f"Total chunks in store: {store.count()}")
    
    # Let's search using the raw keyword ilike matching to see if it even exists
    res = store.client.table(store.table_name).select("id, text, metadata").ilike("text", "%Multi targets concept%").limit(5).execute()
    print(f"\nKeyword search for 'Multi targets concept':")
    if res.data:
        for r in res.data:
            print(f"ID: {r.get('id')}")
            print(f"Text snippet: {r.get('text')[:150]}...")
            print(f"Metadata: {r.get('metadata')}")
            print("-" * 20)
    else:
        print("No matches found for 'Multi targets concept'.")

    res2 = store.client.table(store.table_name).select("id, text, metadata").ilike("text", "%Operator table maintenance%").limit(5).execute()
    print(f"\nKeyword search for 'Operator table maintenance':")
    if res2.data:
        for r in res2.data:
            print(f"ID: {r.get('id')}")
            print(f"Text snippet: {r.get('text')[:150]}...")
            print(f"Metadata: {r.get('metadata')}")
            print("-" * 20)
    else:
        print("No matches found for 'Operator table maintenance'.")

if __name__ == "__main__":
    run_test()
