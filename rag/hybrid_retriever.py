import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

class HybridRetriever:
    """
    Combines Dense Vector Similarity Search with BM25 Keyword Search
    and applies Reciprocal Rank Fusion (RRF) & Reranking.
    """

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self._bm25_index = None
        self._bm25_docs = []
        self._bm25_corpus = []

    def _build_bm25_index(self):
        """Builds BM25 index from all documents currently in the vector store."""
        try:
            if hasattr(self.vector_store, "collection"):
                all_data = self.vector_store.collection.get(include=["documents", "metadatas"])
                if all_data and all_data.get("documents"):
                    self._bm25_docs = []
                    tokenized_corpus = []
                    for i, doc_text in enumerate(all_data["documents"]):
                        meta = all_data["metadatas"][i] if all_data.get("metadatas") else {}
                        doc_id = all_data["ids"][i] if all_data.get("ids") else f"doc_{i}"
                        self._bm25_docs.append({
                            "id": doc_id,
                            "text": doc_text,
                            "metadata": meta
                        })
                        tokens = re.findall(r"\w+", doc_text.lower())
                        tokenized_corpus.append(tokens)

                    if tokenized_corpus:
                        self._bm25_index = BM25Okapi(tokenized_corpus)
        except Exception as e:
            print(f"[HybridRetriever Warning] Could not build BM25 index: {e}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search (Vector + BM25) with Reciprocal Rank Fusion.
        alpha: Weight for dense vector search (1.0 = pure vector, 0.0 = pure BM25, 0.5 = balanced).
        """
        # 1. Dense Vector Search (fetch top 15 candidates)
        candidate_k = max(top_k * 3, 15)
        vector_results = self.vector_store.search(
            query=query,
            top_k=candidate_k,
            category_filter=category
        )

        # 2. BM25 Search
        bm25_results = []
        if not self._bm25_index:
            self._build_bm25_index()

        if self._bm25_index and self._bm25_docs:
            query_tokens = re.findall(r"\w+", query.lower())
            if query_tokens:
                doc_scores = self._bm25_index.get_scores(query_tokens)
                scored_indices = sorted(
                    range(len(doc_scores)),
                    key=lambda idx: doc_scores[idx],
                    reverse=True
                )[:candidate_k]

                for idx in scored_indices:
                    if doc_scores[idx] > 0:
                        item = self._bm25_docs[idx]
                        if not category or category == "General" or item.get("metadata", {}).get("category") == category:
                            bm25_results.append({
                                "id": item["id"],
                                "text": item["text"],
                                "metadata": item["metadata"],
                                "distance": float(doc_scores[idx])
                            })

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        # Score vector results
        for rank, item in enumerate(vector_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + (alpha / (rrf_k + rank + 1))
            doc_map[doc_id] = item

        # Score BM25 results
        for rank, item in enumerate(bm25_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + ((1.0 - alpha) / (rrf_k + rank + 1))
            if doc_id not in doc_map:
                doc_map[doc_id] = item

        # Sort combined results by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda d_id: scores[d_id], reverse=True)
        top_candidates = [doc_map[d_id] for d_id in sorted_ids[:top_k]]

        return top_candidates
