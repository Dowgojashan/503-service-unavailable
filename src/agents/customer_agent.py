from src.agents.base import BaseAgent

class CustomerAgent(BaseAgent):
    """
    Customer Agent: Simulates a human customer with a specific persona and task.
    """
    def __init__(self, model_name="gemini-3.1-flash-lite", persona_instruction=None, fact_sheet=None):
        # Fix: Read task from fact_sheet["agent_input"]
        task_description = fact_sheet.get("agent_input", "")
        # metadata contains intent
        intent = fact_sheet.get("metadata", {}).get("intent", "general inquiry")
        
        # State tracking to prevent redundant openings
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
4. **NO REPETITION**: Once you have stated your problem, do NOT repeat the entire opening or problem description in later turns. Focus only on answering the agent's specific questions.
5. **STATE LOCK**: If this is Turn 2 or later (you have already initiated), you are ABSOLUTELY FORBIDDEN from using your opening template. Just continue the conversation naturally.

IMPORTANT OUTPUT RULE:
- Only output the actual text you want to say to the service agent.
- DO NOT include any internal thoughts, reasoning, drafts, or headers.
- DO NOT use ReAct format (Thought/Action/Final Answer). Just output the message.
- **CONCISENESS**: If the agent asks for information (like Order ID), just provide the information or answer the question directly.

Initiate the conversation by stating your problem briefly."""
        super().__init__(model_name, system_instruction)

    def run(self, last_agent_response, case_id=None):
        """
        Respond to the customer service agent.
        """
        self.turn_count += 1
        
        if not last_agent_response:
            if self.has_initiated:
                # If we were asked to 'start' but already did, it's an error in runner logic
                return "I'm still waiting for your help with my earlier request.", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            prompt = "Please start the conversation with the service agent."
            self.has_initiated = True
        else:
            prompt = f"Service Agent: {last_agent_response}\n\n[TURN {self.turn_count}] Your response (Stay in character, be direct, do NOT repeat your opening):"
        
        response_text, usage = self._call_llm(prompt)
        
        self.history.append({"role": "agent", "content": last_agent_response})
        self.history.append({"role": "customer", "content": response_text})
        
        return response_text, usage
