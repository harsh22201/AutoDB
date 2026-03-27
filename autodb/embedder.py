from sentence_transformers import SentenceTransformer
import torch
from typing import List, Union, Optional
import numpy as np

class Embedder:
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

    def __init__(
        self,
        model_name: str = "all-mpnet-base-v2",
        normalize_embeddings: bool = True
    ):
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Model must be one of {self.AVAILABLE_MODELS}")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model:SentenceTransformer = SentenceTransformer(model_name, device=self.device)
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
            # show_progress_bar=isinstance(texts, list),
            batch_size=32
        )

    # -------------------------------------------------
    # Similarity Functions
    # -------------------------------------------------
    def similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and document embeddings.
        """
        if self.normalize_embeddings:
            # Cosine similarity is just dot product for normalized vectors
            return np.dot(doc_embeddings, query_embedding)
        else:
            # If not normalized, compute cosine similarity manually
            query_norm = np.linalg.norm(query_embedding)
            doc_norms = np.linalg.norm(doc_embeddings, axis=1)
            dot_product = np.dot(doc_embeddings, query_embedding)
            return dot_product / (doc_norms * query_norm + 1e-10)  # Add small epsilon to avoid division by zero


if __name__ == "__main__":
    embeddor = Embedder(model_name="multi-qa-MiniLM-L6-cos-v1")
    docs = [
        "products for health care"
    ]
    
    query = "health care products"
    doc_embeddings = embeddor.embed(docs)
    query_embedding = embeddor.embed(query)
    similarities = embeddor.similarity(query_embedding, doc_embeddings)
    similarities = embeddor.model.similarity(query_embedding, doc_embeddings)
    print(similarities)