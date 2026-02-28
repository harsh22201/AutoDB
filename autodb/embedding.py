from sentence_transformers import SentenceTransformer
import torch
from typing import List, Union, Optional
import numpy as np


class Embeddor:
    """
    Embedding class optimized for retrieval tasks.
    Supports similarity scoring and search.
    Runs comfortably on ~4GB VRAM with MiniLM models.
    """

    AVAILABLE_MODELS = [
        "all-MiniLM-L6-v2",
        "all-MiniLM-L12-v2",
        "paraphrase-MiniLM-L6-v2",
        "multi-qa-MiniLM-L6-cos-v1",
        "all-mpnet-base-v2",
    ]

    AVAILABLE_METRICS = ["cosine", "dot", "euclidean"]

    def __init__(
        self,
        model_name: str = "all-mpnet-base-v2",
        normalize_embeddings: bool = True
    ):
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Model must be one of {self.AVAILABLE_MODELS}")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=self.device)
        self.normalize_embeddings = normalize_embeddings

    # -------------------------------------------------
    # Unified Embedding
    # -------------------------------------------------
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Embed single string or list of strings.
        """
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=isinstance(texts, list),
            batch_size=32
        )

    # -------------------------------------------------
    # Similarity Functions
    # -------------------------------------------------
    def similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray,
        metric: str = "cosine"
    ) -> np.ndarray:
        """
        Compute similarity scores between query and documents.
        """
        if metric not in self.AVAILABLE_METRICS:
            raise ValueError(f"Metric must be one of {self.AVAILABLE_METRICS}")

        if metric == "cosine":
            if not self.normalize_embeddings:
                # normalize manually if needed
                query_embedding = query_embedding / np.linalg.norm(query_embedding)
                doc_embeddings = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
            return np.dot(doc_embeddings, query_embedding)

    # -------------------------------------------------
    # Index Documents
    # -------------------------------------------------
    def index(self, documents: List[str]):
        """
        Store and embed documents for later search.
        """
        self.documents = documents
        self.doc_embeddings = self.embed(documents)

    # -------------------------------------------------
    # Search
    # -------------------------------------------------
    def search(
        self,
        query: str,
        documents: Optional[List[str]] = None,
        top_k: int = 5,
        threshold: Optional[float] = None,
        metric: str = "cosine"
    ):
        """
        Search for most similar documents.

        If documents provided → embeds on the fly.
        If not → uses indexed documents.
        """

        if documents is not None:
            doc_embeddings = self.embed(documents)
        else:
            if self.doc_embeddings is None:
                raise ValueError("No indexed documents found. Call index() first.")
            doc_embeddings = self.doc_embeddings
            documents = self.documents

        query_embedding = self.embed(query)

        scores = self.similarity(query_embedding, doc_embeddings, metric)

        # Sort by descending score
        ranked_indices = np.argsort(scores)[::-1]

        results = []
        for idx in ranked_indices[:top_k]:
            score = scores[idx]

            if threshold is not None and score < threshold:
                continue

            results.append({
                "document": documents[idx],
                "score": float(score),
                "index": int(idx)
            })

        return results
    
    
if __name__ == "__main__":
    embeddor = Embeddor()
    docs = [
        "What are the top selling products in the last month?",
        "List customers with expenditure greater than 10000.",
        "Show me the sales trend for the last quarter."
    ]
    embeddor.index(docs)
    
    query = "Which products sold the most recently?"
    results = embeddor.search(query, top_k=2)
    print(results)