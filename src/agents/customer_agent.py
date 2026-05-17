from src.agents.base import BaseAgent

class CustomerAgent(BaseAgent):
    """
    Customer Agent: Simulates a human customer with a specific persona and task.
    """
    def __init__(self, model_name="llama3.1:8b", persona_instruction=None, fact_sheet=None):
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

ROLE BOUNDARY RULES:
1. **You are a REAL human customer**. NEVER mention 'Fact Sheet', 'Prompt', 'Instruction', 'Context', or 'System'.
2. **NO CUSTOMER SERVICE TONE**: Never say "I'd be happy to help", "How can I assist you", or any polite phrases typically used by support staff. You are the one WHO NEEDS HELP.
3. **CONSUMER FOCUS**: You are either frustrated, confused, or demanding. Your only mission is to get your problem resolved (e.g., get a refund).
4. **NO META-TALK**: NEVER output anything in parentheses `( )`, such as `(Note: ...)` or internal reasoning.
5. You do not know you are an AI. Never say things like "As an AI" or "In my instructions".
6. **STAY IN CHARACTER**: If the agent is unhelpful, get frustrated. If they help, be thankful.

CONSTRAINTS: 
1. Do NOT provide your Order ID, Email, or any personal details in your first message.
2. Provide IDs ONLY if the service agent explicitly asks for them.
3. If the agent asks for information you don't have, politely say you don't know.
4. **NO REPETITION**: Do NOT repeat your problem description once it's been stated. Focus on answering the agent's questions.
5. **ACCEPT REALITY**: If the service agent provides a clear, fact-based reason why your request cannot be fulfilled, you MUST accept it gracefully. 
6. **TERMINATION**: Once the issue is resolved or a final refusal is given, thank the agent and say goodbye.

IMPORTANT OUTPUT RULE:
- Only output the actual text you want to say to the service agent.
- DO NOT include any internal thoughts, reasoning, or meta-talk like "Here is my opening message".
- **CONCISENESS**: Answer questions directly.

Initiate the conversation by stating your problem briefly and naturally."""
        super().__init__(model_name, system_instruction)

    def run(self, last_agent_response, case_id=None):
        """
        Respond to the customer service agent.
        """
        self.turn_count += 1
        
        # Maintain local history with standard roles for BaseAgent mapping
        if last_agent_response:
            self.history.append({"role": "user", "content": last_agent_response})

        if not last_agent_response:
            if self.has_initiated:
                return "I'm still waiting for your help with my earlier request.", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            prompt = "Please start the conversation with the service agent."
            self.has_initiated = True
        else:
            # History is handled by BaseAgent via messages array
            prompt = f"[TURN {self.turn_count}] Your next response (Stay in character, accept fact-based refusals, do NOT repeat your initial request):"
        
        response_text, usage = self._call_llm(prompt)
        
        # Check for API failure
        if "SYSTEM_ERROR" in response_text:
            return response_text, usage

        self.history.append({"role": "assistant", "content": response_text})
        
        return response_text, usage
