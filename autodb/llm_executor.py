from autodb.lm import LM
from autodb.prompts import LLM_EXECUTOR_MSSG

class LLM_Executor:
    def __init__(self, model: str):
        self.llm = LM(model=model)

    def execute(self, sql_result, unstructured_query: str, original_query: str = "") -> str:
        """
        Takes the structured SQL result and the unstructured query,
        and generates the final answered using the LLM.
        """
        # Convert dataframe to string if it's not already
        if hasattr(sql_result, 'to_markdown'):
            sql_result_str = sql_result.to_markdown(index=False)
        else:
            sql_result_str = str(sql_result)

        messages = LLM_EXECUTOR_MSSG + [
            {
                "role": "user",
                "content": (
                    f"Original User Query: {original_query}\n\n"
                    f"Structured SQL Result:\n{sql_result_str}\n\n"
                    f"Unstructured Query:\n{unstructured_query}"
                )
            }
        ]
        
        response = self.llm(messages)
        return response
