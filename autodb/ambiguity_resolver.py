from lm import LM
from prompts import INTENT_AMBIGUITY_DETECTOR_MSSG, VALUE_AMBIGUITY_DETECTOR_MSSG 
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
            ambiguity_key = ambiguity["ambiguity_key"]
            context_key = ambiguity["context_key"]
            llm_options = ambiguity["options"]

            # -----------------------------
            # Display (universal)
            # -----------------------------
            print("\n----------------------------------")
            print(f"Ambiguity {idx}: [{ambiguity_type}] {clarification_question}")
            print(f"Key: {context_key} | {ambiguity_key}")

            # -----------------------------
            # 🔎 SEARCH KNOWLEDGE STORE
            # -----------------------------
            retrieved = self.knowledge_store.search(ambiguity_key, context_key)

            if retrieved:
                print(f"Found! [{retrieved['context_key']}: {retrieved['context_score']:.2f}, {retrieved['ambiguity_key']}: {retrieved['ambiguity_score']:.2f}]")
                stored_options = retrieved["options"]  # top 3 with percentages

                # Display with percentages
                display_options = []
                for opt in stored_options:
                    display_options.append(f"{opt['text']} ({opt['percentage']}%)")

                user_text, is_manual = self._get_user_choice(display_options)

                # Strip percentage suffix if user selected a numbered option
                if not is_manual:
                    # Extract original text (remove the " (XX.X%)" suffix)
                    for opt in stored_options:
                        if user_text == f"{opt['text']} ({opt['percentage']}%)":
                            user_text = opt["text"]
                            break

                # Always update store with selection
                self.knowledge_store.update(
                    ambiguity_key = retrieved["ambiguity_key"],
                    context_key = retrieved["context_key"],
                    selected_option=user_text,
                )

            else:
                # -----------------------------
                # Ask user normally (first time)
                # -----------------------------
                user_text, _ = self._get_user_choice(llm_options)

                # STORE ALL LLM OPTIONS — selected gets count 1, rest get 0
                self.knowledge_store.update(
                    ambiguity_key,
                    context_key,
                    selected_option=user_text,
                    all_options=llm_options
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

class ValueAmbiguityDetector:
    def __init__(self, model: str = "openai/gpt-oss-120b"):
        self.llm = LM(model = model)

    def detect(self, query):
        messages = VALUE_AMBIGUITY_DETECTOR_MSSG + [{"role": "user", "content": f"Query: {query}"}]
        response = self.llm(messages)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not valid JSON: {response}")


if __name__ == "__main__":
    iad = IntentAmbiguityResolver()
    result = iad.resolve("Why are eco-friendly cosmetic products performing poorly among premium customers?")
    print(result)
