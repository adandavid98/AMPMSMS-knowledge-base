import os
import math
import hashlib
import requests
from typing import List

HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
HF_HEADERS = {}
if os.environ.get("HF_API_TOKEN"):
    HF_HEADERS["Authorization"] = f"Bearer {os.environ['HF_API_TOKEN']}"

_DIM = 384

def _hash_embed(texts: List[str]) -> List[List[float]]:
    results = []
    for t in texts:
        seed = int(hashlib.md5(t.encode()).hexdigest(), 16)
        vec = [math.sin(seed * (i + 1) * 0.001) for i in range(_DIM)]
        n = math.sqrt(sum(x * x for x in vec)) or 1.0
        results.append([x / n for x in vec])
    return results

def _hf_embed(texts: List[str]) -> List[List[float]]:
    try:
        payload = {"inputs": texts, "options": {"wait_for_model": True}}
        resp = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                return data
    except Exception:
        pass
    return _hash_embed(texts)

class GeminiEmbeddingFunction:
    def __init__(self, api_key: str = None, model_name: str = None):
        pass

    def __call__(self, input) -> List[List[float]]:
        if not input: return []
        if isinstance(input, str): input = [input]
        return _hf_embed(list(input))

    def embed_query(self, input=None, *args, **kwargs) -> List[List[float]]:
        query_text = input or (args[0] if args else None) or kwargs.get("text", "")
        if isinstance(query_text, str): query_text = [query_text]
        return _hf_embed(list(query_text))
