import os
from abc import ABC, abstractmethod
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class BaseAgent(ABC):
    def __init__(self, model_name="gemini-1.5-flash", system_instruction=None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        self.history = []

    @abstractmethod
    def run(self, user_input, case_id=None):
        """
        Execute the agent logic.
        """
        pass

    def _call_llm(self, prompt):
        """
        Helper to call the LLM and return the text response.
        """
        response = self.model.generate_content(prompt)
        return response.text
