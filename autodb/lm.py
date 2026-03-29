import time
from typing import List, Dict
from groq import Groq
from requests.exceptions import RequestException
from dotenv import load_dotenv
import os

load_dotenv()

class LM:
    """
    A class for making language model calls to Groq API with retries,
    error handling, and optional browser search support.
    """

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b",
        api_key: str|None = os.getenv("GROQ_API_KEY"),
        retries: int = 3,
        temperature: float = 0.0,
    ):
        self.model = model
        self.client = Groq(api_key=api_key)
        self.retries = retries
        self.temperature = temperature

    def get_model(self) -> str:
        return self.model

    def __call__(self, messages: List[Dict[str, str]]) -> str:
        """
        Make a chat completion request to Groq API.

        Args:
            messages (List[Dict[str, str]]): List of message dicts with 'role' and 'content'
        """
        
        # Base parameters
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "seed": 42,
        }

        for attempt in range(1, self.retries + 1):
            try:
                chat_completion = self.client.chat.completions.create(**params)
                response = chat_completion.choices[0].message.content or ""
                return response.strip()

            except RequestException as e:
                print(f"(attempt {attempt}/{self.retries}) Request error: {e}")
            except Exception as e:
                print(f"(attempt {attempt}/{self.retries}) Unexpected error: {e}")

            if attempt < self.retries:
                time.sleep(1)

        raise Exception(f"Failed to get response from Groq API after {self.retries} retries.")


if __name__ == "__main__":
    lm = LM()
    test_messages = [
        {"role": "system", "content": "you are chat bot"},
        {"role": "user", "content": "what is log base 21 of 9892412454323.2134124 show final answer"}
    ]
    response = lm(test_messages)
    print("LM Response:", response)