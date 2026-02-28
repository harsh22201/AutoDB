import json
import os
import numpy as np
from embedder import Embedder


class AmbiguityKnowledgeStore:

    def __init__(
        self,
        path="ambiguity_store.json",
        similarity_threshold=0.85,
        embedder=None
    ):
        self.path = path
        self.similarity_threshold = similarity_threshold
        self.embedder = embedder or Embedder()

        self.data = self._load()

    # -------------------------
    # Load / Save
    # -------------------------
    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                return json.load(f)
        return {"entries": []}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    # -------------------------
    # Search similar ambiguity
    # -------------------------
    def search(self, ambiguity_label):
        """
        Returns:
            {
                "found": bool,
                "clarifications": [...]
            }
        """

        if not self.data["entries"]:
            return {"found": False}

        query_emb = self.embedder.embed(ambiguity_label)

        stored_embeddings = np.array([
            entry["embedding"]
            for entry in self.data["entries"]
        ])

        similarities = self.embedder.similarity(
            query_emb,
            stored_embeddings
        )

        best_idx = int(np.argmax(similarities))
        best_score = similarities[best_idx]

        if best_score >= self.similarity_threshold:
            return {
                "found": True,
                "clarifications":
                    self.data["entries"][best_idx]["clarifications"],
                "score": float(best_score)
            }

        return {"found": False}

    # -------------------------
    # Update store
    # -------------------------
    def update(self, ambiguity_label, clarifications):
        """
        Add new ambiguity knowledge.
        """

        embedding = self.embedder.embed(ambiguity_label).tolist()

        self.data["entries"].append({
            "ambiguity_label": ambiguity_label,
            "embedding": embedding,
            "clarifications": clarifications
        })

        self._save()