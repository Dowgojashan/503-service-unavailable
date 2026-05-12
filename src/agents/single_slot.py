from src.agents.base import BaseAgent

class SingleSlotAgent(BaseAgent):
    """
    Single-slot Agent: Performs a single LLM call to generate a response.
    Suitable as a baseline for zero-shot performance.
    """
    def run(self, user_input, case_id=None):
        # In a real scenario, we might provide tool outputs as context here 
        # if this were a RAG-style single call, but for this experiment, 
        # it represents the simplest direct response mode.
        prompt = f"User Input: {user_input}\n\nPlease provide a professional response based on your instructions."
        response_text = self._call_llm(prompt)
        
        # Log to history
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response_text})
        
        return response_text
