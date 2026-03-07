import json
import os
import numpy as np
from embedder import Embedder


class AmbiguityKnowledgeStore:

    def __init__(
        self,
        path="ambiguity_store.json",
        similarity_threshold=0.70,
        recent_k=5,
        embedder=None
    ):
        self.path = path
        self.embeddings_path = os.path.splitext(path)[0] + "_embeddings.npy" 
        self.similarity_threshold = similarity_threshold
        self.recent_k = recent_k
        self.embedder = embedder or Embedder()

        self.data = self._load_store()
        self.embeddings = self._load_embeddings()

    # -------------------------
    # Load / Save — JSON
    # -------------------------
    def _load_store(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                return json.load(f)
        return {"entries": []}

    def _save_store(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    # -------------------------
    # Load / Save — Embeddings
    # -------------------------
    def _load_embeddings(self):
        if os.path.exists(self.embeddings_path):
            return np.load(self.embeddings_path)
        return np.empty((0, 0))

    def _save_embeddings(self):
        np.save(self.embeddings_path, self.embeddings)

    # -------------------------
    # Search similar ambiguity
    # -------------------------
    def search(self, ambiguity_label):
        """
        Returns:
            {
                "ambiguity_label": str,
                "clarifications": [...],
                "score": float
            }
            or {} if no match found.
        """

        if len(self.data["entries"]) == 0 or self.embeddings.size == 0:
            return {}

        query_emb = self.embedder.embed(ambiguity_label)

        similarities = self.embedder.similarity(
            query_emb,
            self.embeddings
        )

        best_idx = int(np.argmax(similarities))
        best_score = similarities[best_idx]

        if best_score >= self.similarity_threshold:
            entry = self.data["entries"][best_idx]
            return {
                "ambiguity_label": entry["ambiguity_label"],
                "clarifications": entry["clarifications"],
                "score": float(best_score)
            }

        return {}

    # -------------------------
    # Update store
    # -------------------------
    def update(self, ambiguity_label, clarifications):
        """
        Add or update ambiguity knowledge.
        Keeps only the most recent k clarifications per entry.
        """

        if type(clarifications) == str:
            clarifications = [clarifications]

        embedding = self.embedder.embed(ambiguity_label)

        # Check if this label already exists (exact match)
        for entry in self.data["entries"]:
            if entry["ambiguity_label"] == ambiguity_label:
                # Merge and keep recent k
                combined = entry["clarifications"] + clarifications
                # Deduplicate while preserving order
                seen = set()
                unique = []
                for c in combined:
                    if c not in seen:
                        seen.add(c)
                        unique.append(c)
                entry["clarifications"] = unique[-self.recent_k:]
                self._save_store()
                return

        # New entry
        self.data["entries"].append({
            "ambiguity_label": ambiguity_label,
            "clarifications": clarifications[-self.recent_k:]
        })

        # Append embedding
        if self.embeddings.size == 0:
            self.embeddings = embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, embedding.reshape(1, -1)])

        self._save_store()
        self._save_embeddings()