"""
Lightweight embedding engine using HuggingFace Inference API.
Uses the same all-MiniLM-L6-v2 model (384-dim) as local ONNX version.
No PyTorch/sentence-transformers needed — works within Vercel's 250MB limit.
"""
import os
import math
import hashlib
import requests
from typing import List

import config

# HuggingFace modern router endpoint (sentence-transformers/all-MiniLM-L6-v2, 384-dim)
HF_API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
_DIM = 384
_warned_missing_hf_token = False

def _hash_embed(texts: List[str]) -> List[List[float]]:
    """Deterministic 384-dim fallback if HuggingFace API is unavailable."""
    results = []
    for t in texts:
        seed = int(hashlib.md5(t.encode()).hexdigest(), 16)
        vec = [math.sin(seed * (i + 1) * 0.001) for i in range(_DIM)]
        n = math.sqrt(sum(x * x for x in vec)) or 1.0
        results.append([x / n for x in vec])
    return results


def _hf_embed(texts: List[str]) -> List[List[float]]:
    """Call HuggingFace Inference API for all-MiniLM-L6-v2 embeddings."""
    global _warned_missing_hf_token
    token = getattr(config, "HF_API_TOKEN", "") or os.environ.get("HF_API_TOKEN", "")
    if not token:
        if not _warned_missing_hf_token:
            print("[Warning] HF_API_TOKEN is not set in .env. Semantic embeddings are falling back to hash vectors. Add HF_API_TOKEN to .env for real embeddings.")
            _warned_missing_hf_token = True
        return _hash_embed(texts)

    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"inputs": texts, "options": {"wait_for_model": True}}
        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], list):
                    return data
        else:
            print(f"[Warning] HuggingFace embedding API returned status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[Warning] HuggingFace embedding request failed: {e}")

    return _hash_embed(texts)


class GeminiEmbeddingFunction:
    """
    Embedding function using HuggingFace Inference API (all-MiniLM-L6-v2, 384-dim).
    Zero heavy dependencies — compatible with Vercel serverless functions.
    """

    def __init__(self, api_key: str = None, model_name: str = None):
        pass

    def __call__(self, input) -> List[List[float]]:
        if not input:
            return []
        if isinstance(input, str):
            input = [input]
        return _hf_embed(list(input))

    def embed_query(self, input=None, *args, **kwargs) -> List[List[float]]:
        query_text = input
        if query_text is None and args:
            query_text = args[0]
        if query_text is None:
            query_text = kwargs.get("text", "")
        if isinstance(query_text, str):
            query_text = [query_text]
        return _hf_embed(list(query_text))
