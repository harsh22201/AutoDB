from lm import LM
from prompts import INTENT_AMBIGUITY_DETECTOR_MSSG, SCHEMA_AMBIGUITY_DETECTOR_MSSG 
import json


class IntentAmbiguityDetector:
    def __init__(self, model: str = "openai/gpt-oss-120b", max_iterations: int = 3):
        self.llm = LM(model=model)
        self.max_iterations = max_iterations

    # -----------------------------
    # Internal LLM call
    # -----------------------------
    def _detect_once(self, query, previous_clarifications):
        messages = INTENT_AMBIGUITY_DETECTOR_MSSG + [
            {
                "role": "user",
                "content": f" Query: {query}\nPrevious Clarifications: {json.dumps(previous_clarifications)}"
            }
        ]

        response = self.llm(messages)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not valid JSON: {response}")

    # -----------------------------
    # Ask user clarification
    # -----------------------------
    def _collect_user_feedback(self, ambiguities):
        """
        Prompts user to either:
        0. provide manual clarification or
        1. choose an option
        """

        clarifications = []

        for idx, amb in enumerate(ambiguities, 1):
            print("\n----------------------------------")
            print(f"Ambiguity {idx}: {amb['ambiguity_label']}")
            print(amb["clarification_question"])
            print("0. Write my own clarification")
            for i, opt in enumerate(amb["options"], 1):
                print(f"{i}. {opt}")

            choice = input("Select option number or 0: ").strip()

            if choice == "0":
                user_text = input("Enter your clarification: ")
            else:
                try:
                    user_text = amb["options"][int(choice) - 1]
                except:
                    user_text = input("Invalid choice. Enter clarification manually: ")

            clarifications.append({
                "ambiguity_label": amb["ambiguity_label"],
                "user_clarification": user_text
            })

        return clarifications

    # -----------------------------
    # PUBLIC LOOP METHOD
    # -----------------------------
    def detect(self, query):
        """
        Runs iterative ambiguity resolution loop.
        """

        clarifications = []

        for iteration in range(self.max_iterations):

            print(f"\n========== Iteration {iteration+1} ==========")

            ambiguities = self._detect_once(
                query = query,
                previous_clarifications = clarifications
            )

            # Stop if no ambiguity
            if not ambiguities:
                print("No remaining ambiguities.")
                break

            # collect feedback
            new_clarifications = self._collect_user_feedback(ambiguities)

            clarifications.extend(new_clarifications)

        return clarifications
        
class SchemaAmbiguityDetector:
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        self.llm = LM(model = model)

    def detect(self, query):
        messages = SCHEMA_AMBIGUITY_DETECTOR_MSSG + [{"role": "user", "content": f"Query: {query}"}]
        response = self.llm(messages)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not valid JSON: {response}")
        
        
if __name__ == "__main__":
    iad = IntentAmbiguityDetector()
    result = iad.detect("show top 5 toothpaste")
    print(result)