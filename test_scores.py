import os
from dotenv import load_dotenv
from vectorstore import VectorStoreManager

load_dotenv()
store = VectorStoreManager()
res = store.search('what are the system database tables', top_k=5)
print('Results count:', len(res))
for i, r in enumerate(res):
    meta = r.get('metadata', {})
    print(f"{i+1}. File: {meta.get('file_name')} | Topic: {meta.get('topic_title')} | Score: {r.get('score')}")
    print('Snippet:', r.get('text', '')[:200])
    print('---')
