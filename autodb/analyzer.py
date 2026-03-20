from autodb.lm import LM
from autodb.prompts import ANALYZER_MSSG
import json

class Analyzer:
    def __init__(self, model: str):
        self.llm = LM(model=model)

    def analyze(self, query: str, clarifications: list[dict] = None):
        messages = ANALYZER_MSSG + [
            {
                "role": "user",
                "content": (
                    f"Query: \"{query}\"\n"
                    f"Clarifications: {json.dumps(clarifications)}"
                ),
            }
        ]
        response = self.llm(messages)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse analysis response: {response}")
            return {}
        