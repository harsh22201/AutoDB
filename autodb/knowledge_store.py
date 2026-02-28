import json
import numpy as np
from embedding import embed_text, cosine_similarity


class AmbiguityKnowledgeStore:

    def __init__(self, path="ambiguity_store.json",
                 similarity_threshold=0.85):

        self.path = path
        self.similarity_threshold = similarity_threshold
        self.data = self._load()

    # -------------------------
    # Load / Save
    # -------------------------
    def _load(self):
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except:
            return []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    # -------------------------
    # Search similar ambiguity
    # -------------------------
    def search(self, ambiguity_label):

        query_vec = embed_text(ambiguity_label)

        best_match = None
        best_score = 0

        for item in self.data:
            score = cosine_similarity(query_vec,
                                      np.array(item["embedding"]))

            if score > best_score:
                best_score = score
                best_match = item

        if best_score >= self.similarity_threshold:
            return best_match["clarifications"]

        return None

    # -------------------------
    # Update store
    # -------------------------
    def add_clarification(self, ambiguity_label, clarification):

        vec = embed_text(ambiguity_label)

        # find existing
        for item in self.data:
            if item["ambiguity_label"] == ambiguity_label:
                if clarification not in item["clarifications"]:
                    item["clarifications"].append(clarification)
                self._save()
                return

        # new entry
        self.data.append({
            "ambiguity_label": ambiguity_label,
            "embedding": vec.tolist(),
            "clarifications": [clarification]
        })

        self._save()