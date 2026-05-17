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
            # This is a tool result, provide final answer
            prompt = f"Observation received: {user_input}\n\nBased on this data, provide a final response to the user. If the issue is resolved, end politely. Do NOT mention tools or internal processes."
        else:
            # Normal user input
            prompt = f"""Current User Input: {user_input}

[DECISION LOGIC]
1. Check dialogue history for Order ID (ORDxxx) or Email.
2. If ID/Email present and you need order data, you MUST output: Action: query_order(order_id="ORDxxx")
3. If you just received an Observation from a tool, use that data to give a FINAL ANSWER.
4. If ID is missing, ask for it politely.
5. For refunds/cancellations: NO date checking needed. Only verify Order ID exists.

[AVAILABLE TOOLS] (See tools_whitelist.txt)
- query_order(order_id="ORDxxx") or query_order(email="user@example.com")
- track_shipping(order_id="ORDxxx")
- apply_refund(order_id="ORDxxx", reason="reason")
- cancel_order(order_id="ORDxxx", reason="reason")

FORBIDDEN: exchange_option, initiate_return, or any tool NOT listed above.

IMPORTANT: If you need to use a tool, output ONLY the Action line and STOP. If you have enough info, output ONLY the Final Answer. Do NOT explain or add extra text."""
        
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
