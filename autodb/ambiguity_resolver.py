from lm import LM
from prompts import INTENT_AMBIGUITY_DETECTOR_MSSG, SCHEMA_AMBIGUITY_DETECTOR_MSSG 
from knowledge_store import AmbiguityKnowledgeStore
import json

class IntentAmbiguityResolver:
    def __init__(self, model: str = "openai/gpt-oss-120b", max_iterations: int = 3):
        self.llm = LM(model=model)
        self.knowledge_store = AmbiguityKnowledgeStore()
        self.max_iterations = max_iterations

    # -----------------------------
    # Internal LLM call
    # -----------------------------
    def _detect_ambiguity(self, query, previous_clarifications):
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

        clarifications = []

        for idx, ambiguity in enumerate(ambiguities, 1):

            ambiguity_label = ambiguity["ambiguity_label"]
            question = ambiguity["clarification_question"]
            options = ambiguity["options"]

            # -----------------------------
            # 🔎 SEARCH KNOWLEDGE STORE
            # -----------------------------
            retrieved = self.knowledge_store.search(ambiguity_label)

            if retrieved["found"]:
                print("\n✅ Found similar past ambiguity!")
                print(f"Ambiguity: {ambiguity_label}")
                print("Previously used clarifications:")

                stored_options = retrieved["clarifications"]

                for i, opt in enumerate(stored_options, 1):
                    print(f"{i}. {opt}")

                choice = input(
                    "Select option (or 0 to override): "
                ).strip()

                if choice == "0":
                    user_text = input("Enter clarification: ")
                else:
                    user_text = stored_options[int(choice) - 1]

            else:
                # -----------------------------
                # Ask user normally
                # -----------------------------
                print("\n----------------------------------")
                print(f"Ambiguity {idx}: {ambiguity_label}")
                print(question)

                print("0. Write clarification manually")
                for i, opt in enumerate(options, 1):
                    print(f"{i}. {opt}")

                choice = input("Select option: ").strip()

                if choice == "0":
                    user_text = input("Enter clarification: ")
                else:
                    user_text = options[int(choice) - 1]

                # ✅ STORE NEW KNOWLEDGE
                self.knowledge_store.update(
                    ambiguity_label,
                    options
                )

            clarifications.append({
                "ambiguity_label": ambiguity_label,
                "user_clarification": user_text
            })

        return clarifications

    # -----------------------------
    # PUBLIC LOOP METHOD
    # -----------------------------
    def resolver(self, query):
        """
        Runs iterative ambiguity resolution loop.
        """

        clarifications = []

        for iteration in range(self.max_iterations):

            print(f"\n========== Iteration {iteration+1} ==========")

            ambiguities = self._detect_ambiguity(
                query = query,
                previous_clarifications = clarifications
            )

            # Stop if no ambiguity
            if not ambiguities:
                print("========== No more ambiguities detected. ==========")
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
    iad = IntentAmbiguityResolver()
    result = iad.resolver("show top 5 toothpaste")
    print(result)