import json
import os
import numpy as np
from embedder import Embedder

class AmbiguityKnowledgeStore:

    def __init__(
        self,
        path="ambiguity_store.json",
        context_threshold=0.80,
        ambiguity_threshold=0.75,
        embedder=None
    ):
        self.path = path
        self.context_threshold = context_threshold
        self.ambiguity_threshold = ambiguity_threshold
        self.embedder = embedder or Embedder()

        self.data = self._load_store()

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
    # Two-stage search
    # -------------------------
    def search(self, ambiguity_key, context_key):
        """
        Two-stage filtering search:
          Stage 1: Filter entries by context_key similarity.
          Stage 2: Among filtered entries, find best ambiguity_key match.

        Returns:
            {
                "ambiguity_key": str,
                "context_key": str,
                "options": [{"text": str, "count": int, "percentage": float}, ...],
                "score": float
            }
            or {} if no match found.
        """

        entries = self.data["entries"]
        if not entries:
            return {}

        # --- Stage 1: Context key filtering ---
        stored_context_keys = [e["context_key"] for e in entries]
        query_context_emb = self.embedder.embed(context_key)
        stored_context_embs = self.embedder.embed(stored_context_keys)

        # Handle single entry case (1-D embedding)
        if stored_context_embs.ndim == 1:
            stored_context_embs = stored_context_embs.reshape(1, -1)

        context_sims = self.embedder.similarity(query_context_emb, stored_context_embs)

        # Filter indices that pass context threshold
        context_candidates = [
            (i, context_sims[i])
            for i in range(len(entries))
            if context_sims[i] >= self.context_threshold
        ]

        if not context_candidates:
            return {}

        # --- Stage 2: Ambiguity key filtering ---
        candidate_indices = [idx for idx, _ in context_candidates]
        stored_ambiguity_keys = [entries[i]["ambiguity_key"] for i in candidate_indices]
        query_ambiguity_emb = self.embedder.embed(ambiguity_key)
        stored_ambiguity_embs = self.embedder.embed(stored_ambiguity_keys)

        if stored_ambiguity_embs.ndim == 1:
            stored_ambiguity_embs = stored_ambiguity_embs.reshape(1, -1)

        ambiguity_sims = self.embedder.similarity(query_ambiguity_emb, stored_ambiguity_embs)

        best_local_idx = int(np.argmax(ambiguity_sims))
        best_score = float(ambiguity_sims[best_local_idx])

        if best_score < self.ambiguity_threshold:
            return {}

        best_entry = entries[candidate_indices[best_local_idx]]

        # Compute percentages and get top 3
        options = best_entry["options"]
        total_count = sum(opt["count"] for opt in options)

        options_with_pct = []
        for opt in options:
            pct = (opt["count"] / total_count * 100) if total_count > 0 else 0.0
            options_with_pct.append({
                "text": opt["text"],
                "count": opt["count"],
                "percentage": round(pct, 1)
            })

        # Sort by count descending, take top 3
        options_with_pct.sort(key=lambda x: x["count"], reverse=True)
        top_3 = options_with_pct[:3]

        return {
            "ambiguity_key": best_entry["ambiguity_key"],
            "context_key": best_entry["context_key"],
            "options": top_3,
            "score": best_score
        }

    # -------------------------
    # Update store
    # -------------------------
    def update(self, ambiguity_key, context_key, selected_option, all_options=None):
        """
        Add or update ambiguity knowledge.

        Args:
            ambiguity_key: The ambiguity category label.
            context_key: The domain entity context.
            selected_option: The option the user chose (str).
            all_options: All LLM-generated options (list of str). Used when
                         creating a new entry to store all options.
        """

        if all_options is None:
            all_options = [selected_option]

        # Check if this exact key pair already exists
        for entry in self.data["entries"]:
            if entry["ambiguity_key"] == ambiguity_key and entry["context_key"] == context_key:
                # Increment count for selected option
                found = False
                for opt in entry["options"]:
                    if opt["text"] == selected_option:
                        opt["count"] += 1
                        found = True
                        break

                # If selected option is new (e.g. user typed manually), add it
                if not found:
                    entry["options"].append({"text": selected_option, "count": 1})

                # Merge any new options from all_options that don't exist yet
                existing_texts = {opt["text"] for opt in entry["options"]}
                for opt_text in all_options:
                    if opt_text not in existing_texts:
                        entry["options"].append({"text": opt_text, "count": 0})

                self._save_store()
                return

        # New entry — store all options, selected gets count 1, rest get 0
        new_options = []
        for opt_text in all_options:
            count = 1 if opt_text == selected_option else 0
            new_options.append({"text": opt_text, "count": count})

        # If selected_option wasn't in all_options, add it too
        if selected_option not in all_options:
            new_options.append({"text": selected_option, "count": 1})

        self.data["entries"].append({
            "ambiguity_key": ambiguity_key,
            "context_key": context_key,
            "options": new_options
        })

        self._save_store()