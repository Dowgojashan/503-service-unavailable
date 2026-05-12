from src.agents.base import BaseAgent

class SingleSlotAgent(BaseAgent):
    """
    Single-slot Agent: Performs a single LLM call per turn, but with full context.
    Suitable as a baseline for zero-shot performance with history.
    """
    def __init__(self, model_name="gemini-2.5-flash", system_instruction=None):
        super().__init__(model_name, system_instruction)

    def run(self, user_input, case_id=None):
        # Construct context-aware prompt
        history_str = "\n".join([f"{h['role'].upper()}: {h['content']}" for h in self.history])
        
        prompt = f"""Conversation History:
{history_str}

Current User Input: {user_input}

[INVISIBLE THINKING]
1. Scan the history above. Has the user provided an Order ID or Email?
2. What was the user's very first request?
3. If verification is complete, provide the final solution or status.
4. If verification is missing, ask for it.

Please provide your professional response:"""
        
        response_text, usage = self._call_llm(prompt)
        
        # Log to history
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response_text})
        
        return response_text, usage
