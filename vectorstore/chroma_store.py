import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import config
from .embeddings import GeminiEmbeddingFunction

class VectorStoreManager:
    """Manages local ChromaDB vector database operations."""

    def __init__(self, persist_dir: str = config.CHROMA_PERSIST_DIR, collection_name: str = config.COLLECTION_NAME):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_fn = GeminiEmbeddingFunction()

        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "AMPM Service POS Documentation Vector Store"}
        )

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Adds or updates document chunks in the vector collection.
        Returns count of added chunks.
        """
        if not chunks:
            return 0

        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]

        # Process in batches of 100
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            self.collection.upsert(
                ids=ids[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size]
            )

        return len(chunks)

    def search(self, query: str, top_k: int = 5, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search.
        Optionally filters by document category.
        Returns formatted result objects with text, metadata, and relevance distance.
        """
        where_clause = None
        if category_filter and category_filter != "General":
            where_clause = {"category": category_filter}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause
        )

        matches = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
            ids = results["ids"][0]

            for i in range(len(docs)):
                matches.append({
                    "id": ids[i],
                    "text": docs[i],
                    "metadata": metas[i],
                    "distance": distances[i]
                })

        return matches

    def count(self) -> int:
        """Returns total document chunks in vector store."""
        return self.collection.count()

    def reset_collection(self):
        """Clears all vectors from the collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn
        )
