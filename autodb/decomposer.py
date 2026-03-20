from lm import LM
from prompts import DECOMPOSER_MSSG
import json

class Decomposer:
    def __init__(self, model: str):
        self.llm = LM(model=model)

    def decompose(self, query: str, analysis: dict, candidates: list[dict] = None):
        """
        Decomposes a query into structured (SQL) and unstructured (LLM) sub-queries
        using the analysis output and optional candidate values for value ambiguity resolution.
        """
        messages = DECOMPOSER_MSSG + [
            {
                "role": "user",
                "content": (
                    f"Original Query: \"{query}\"\n"
                    f"Analysis: {json.dumps(analysis)}\n"
                    f"Candidates: {json.dumps(candidates)}"
                ),
            }
        ]
        response = self.llm(messages)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse analysis response: {response}")
            return {}
        