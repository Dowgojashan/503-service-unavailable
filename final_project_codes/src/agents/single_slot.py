from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class SingleSlotAgent(BaseAgent):
    """
    Single-slot Agent: Performs a single LLM call per turn, but with full context.
    Suitable as a baseline for zero-shot performance with history.
    """
    def __init__(self, model_name="llama3.1:8b", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        # Check if this is an observation response
        if "Observation:" in user_input:
            prompt = (
                f"{user_input}\n\n"
                "The system has returned the above Observation. "
                "Use ONLY the data in that Observation to write your response to the customer. "
                "Do NOT mention tools, 'Action', 'Observation', or any internal process. "
                "Respond naturally and professionally. If the task is complete, end the conversation politely."
            )
        else:
            # Normal user input
            prompt = f"""Customer message: {user_input}

[YOUR DECISION — choose exactly one option and output only that]:

OPTION A — Order ID or Email IS in the dialogue history and you need order data:
  Output exactly: Action: query_order(order_id="ORDxxx")
  Then STOP. Write absolutely nothing after the Action line.
  DO NOT say "I've checked", "I can see", "Your order is", or anything implying you already have data.

OPTION B — Order ID/Email is NOT in the dialogue history:
  Ask the customer for their Order ID (ORDxxx format) or registered email. Nothing else.

OPTION C — You already received an Observation earlier in this conversation and need to take a follow-up action:
  Based on the Observation data, call the appropriate next tool:
  - apply_refund(order_id="ORDxxx", reason="Customer request")
  - cancel_order(order_id="ORDxxx", reason="Customer request")
  - track_shipping(order_id="ORDxxx")
  Then STOP. Write nothing after the Action line.

[FORBIDDEN — these are hallucinations]:
- "I've checked your order..." (before receiving Observation)
- "I can confirm..." (before receiving Observation)
- "Your order is currently..." (before receiving Observation)
- Writing any order details, status, amount, or item names you have NOT seen in an Observation.
- Simulating or predicting what the tool result might be.

[TOOLS — exact format required]:
  Action: query_order(order_id="ORDxxx")
  Action: query_order(email="user@example.com")
  Action: apply_refund(order_id="ORDxxx", reason="Customer request")
  Action: cancel_order(order_id="ORDxxx", reason="Customer request")
  Action: track_shipping(order_id="ORDxxx")

[OUTPUT DISCIPLINE — strictly enforced]:
- Your response is ONLY the words you speak to the customer. Nothing else.
- NEVER say things like "Since the Order ID is not in the dialogue history..." or "Based on OPTION A..." — that is internal reasoning and must never appear in your output.
- NEVER say "I'm going to process X" or "I will now call X" — just output the Action line and stop. Do it, don't announce it.
- If the task is complete, end with one polite closing sentence. Then stop. Do NOT say "This conversation is now closed" as a system announcement."""
        
        response_text, usage = self._call_llm(prompt)
        
        # Log to history
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response_text})
        
        return response_text, usage

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id: return "Error: case_id is required."
        try:
            if tool_name == "query_order": 
                return self.simulator.query_order(case_id, tool_args)
            elif tool_name == "track_shipping": 
                return self.simulator.track_shipping(case_id, tool_args)
            elif tool_name == "apply_refund": 
                return self.simulator.apply_refund(case_id, tool_args)
            elif tool_name == "cancel_order":
                return self.simulator.cancel_order(case_id, tool_args)
            else: 
                return f"Error: Tool '{tool_name}' not found. Only query_order, track_shipping, apply_refund, cancel_order are allowed."
        except Exception as e:
            return f"Error executing tool: {str(e)}"
