from lm import LM
from prompts import INTENT_AMBIGUITY_DETECTOR_MSSG, SCHEMA_AMBIGUITY_DETECTOR_MSSG 
from knowledge_store import AmbiguityKnowledgeStore
import json

class IntentAmbiguityResolver:
    def __init__(self, model: str = "openai/gpt-oss-120b", max_iterations: int = 3):
        self.llm = LM(model=model, temperature=0)
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
    # -----------------------------
    # Get user choice (shared)
    # -----------------------------
    def _get_user_choice(self, available_options):
        """
        Auto-detects whether user input is a number (option selection)
        or a string (manual clarification). Includes error handling.
        """

        for i, opt in enumerate(available_options, 1):
            print(f"{i}. {opt}")

        while True:
            choice = input("Select option or type manually: ").strip()

            if not choice:
                print("⚠️ Empty input. Please select an option or type your clarification.")
                continue

            try:
                idx = int(choice)
                if 1 <= idx <= len(available_options):
                    return available_options[idx - 1], False
                else:
                    print(f"⚠️ Invalid option. Please enter a number between 1 and {len(available_options)}, or type your clarification.")
            except ValueError:
                # Not a number — treat as manual clarification
                return choice, True

    # -----------------------------
    # Collect user feedback
    # -----------------------------
    def _collect_user_feedback(self, ambiguities):

        clarifications = []

        for idx, ambiguity in enumerate(ambiguities, 1):

            ambiguity_type = ambiguity["ambiguity_type"]
            clarification_question = ambiguity["clarification_question"]
            ambiguity_label = ambiguity["ambiguity_label"]
            options = ambiguity["options"]

            # -----------------------------
            # Display (universal)
            # -----------------------------
            print("\n----------------------------------")
            print(f"Ambiguity {idx}: [{ambiguity_type}] {clarification_question}")
            print(f"Ambiguity Label: {ambiguity_label}")

            # -----------------------------
            # 🔎 SEARCH KNOWLEDGE STORE
            # -----------------------------
            retrieved = self.knowledge_store.search(ambiguity_label)

            if retrieved:
                print(f"Found similar past ambiguity! [{retrieved['ambiguity_label']}|{retrieved['score']:.2f}]")
                print("Previously used clarifications:")
                stored_options = retrieved["clarifications"]
                user_text, is_manual = self._get_user_choice(stored_options)

                # Only update store if user typed manually
                if is_manual:
                    self.knowledge_store.update(
                        ambiguity_label,
                        user_text
                    )

            else:
                # -----------------------------
                # Ask user normally
                # -----------------------------
                user_text, _ = self._get_user_choice(options)

                # STORE NEW KNOWLEDGE (only the chosen/typed clarification)
                self.knowledge_store.update(
                    ambiguity_label,
                    user_text
                )

            clarifications.append({
                "clarification_question": clarification_question,
                "user_clarification": user_text
            })

        return clarifications

    # -----------------------------
    # PUBLIC LOOP METHOD
    # -----------------------------
    def resolve(self, query):
        """
        Runs iterative ambiguity resolution loop.
        """

        clarifications = []

        for iteration in range(self.max_iterations):

            print(f"\n========== Iteration {iteration+1} ==========")

            ambiguity = self._detect_ambiguity(
                query = query,
                previous_clarifications = clarifications
            )

            # Stop if no ambiguity
            if not ambiguity:
                print("========== No more ambiguities detected ==========")
                break

            # collect feedback
            new_clarifications = self._collect_user_feedback(ambiguity)
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
    result = iad.resolve("show top 5 toothpaste")
    print(result)
