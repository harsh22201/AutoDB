import json
import numpy as np
import os


class AmbiguityKnowledgeStore:

    def __init__(self, path="ambiguity_store.json",
                similarity_threshold=0.85):

        self.path = path
        self.similarity_threshold = similarity_threshold
        self.data = self._load()

    # -------------------------
    # Load / Save
    # -------------------------
    def _load(self)-> dict:
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    # -------------------------
    # Search similar ambiguity
    # -------------------------
    def search(self, ambiguity_label):
        pass

    # -------------------------
    # Update store
    # -------------------------
    def update(self, ambiguity_label, clarifications):
        pass
