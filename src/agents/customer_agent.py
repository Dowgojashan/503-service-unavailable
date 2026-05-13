from src.agents.base import BaseAgent

class CustomerAgent(BaseAgent):
    """
    Customer Agent: Simulates a human customer with a specific persona and task.
    """
    def __init__(self, model_name="gemma-4-31b-it", persona_instruction=None, fact_sheet=None):
        # Fix: Read task from fact_sheet["agent_input"]
        task_description = fact_sheet.get("agent_input", "")
        # metadata contains intent
        intent = fact_sheet.get("metadata", {}).get("intent", "general inquiry")
        
        # State tracking
        self.has_initiated = False
        self.turn_count = 0
        
        # Combine persona and task into a single system instruction
        system_instruction = f"""{persona_instruction}

Your primary intent is: {intent}
Your specific goal is: {task_description}

CONSTRAINT: 
1. Do NOT provide your Order ID, Email, or any personal details in your first message.
2. Provide IDs ONLY if the service agent explicitly asks for them.
3. If the agent asks for information you don't have, politely say you don't know.
4. **NO REPETITION**: Do NOT repeat your problem description once it's been stated. Focus on answering the agent's questions.
5. **ACCEPT REALITY**: If the service agent provides a clear, fact-based reason why your request cannot be fulfilled (e.g., order has already shipped, item is outside return window), and they have verified this via their system, you MUST accept the answer gracefully. 
6. **TERMINATION**: Once the issue is resolved or a final refusal is given, thank the agent and say goodbye (e.g., "Thank you for your help. Goodbye." or "I understand, thank you. Have a nice day.").

IMPORTANT OUTPUT RULE:
- Only output the actual text you want to say to the service agent.
- DO NOT include any internal thoughts, reasoning, drafts, or headers.
- **CONCISENESS**: Answer questions directly.

Initiate the conversation by stating your problem briefly."""
        super().__init__(model_name, system_instruction)

    def run(self, last_agent_response, case_id=None):
        """
        Respond to the customer service agent.
        """
        self.turn_count += 1
        
        # Maintain local history
        if last_agent_response:
            self.history.append({"role": "agent", "content": last_agent_response})

        if not last_agent_response:
            if self.has_initiated:
                return "I'm still waiting for your help with my earlier request.", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            prompt = "Please start the conversation with the service agent."
            self.has_initiated = True
        else:
            # Build history context to ensure state awareness
            history_context = ""
            # Only include recent history to keep it focused
            for h in self.history[-10:]:
                role = "Service Agent" if h['role'] == "agent" else "You (Customer)"
                history_context += f"{role}: {h['content']}\n"

            prompt = f"--- Conversation History ---\n{history_context}\n\n[TURN {self.turn_count}] Your next response (Stay in character, accept fact-based refusals, do NOT repeat your initial request):"
        
        response_text, usage = self._call_llm(prompt)
        
        # Check for API failure
        if "SYSTEM_ERROR" in response_text:
            return response_text, usage

        self.history.append({"role": "customer", "content": response_text})
        
        return response_text, usage
