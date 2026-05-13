from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class SingleSlotAgent(BaseAgent):
    """
    Single-slot Agent: Performs a single LLM call per turn, but with full context.
    Suitable as a baseline for zero-shot performance with history.
    """
    def __init__(self, model_name="gemini-3.1-flash-lite", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        # Construct context-aware prompt
        history_str = ""
        for h in self.history[-10:]:
            role = h['role'].upper()
            content = h['content']
            history_str += f"{role}: {content}\n"
        
        prompt = f"""Conversation History:
{history_str}

Current User Input: {user_input}

[DECISION LOGIC]
1. If user provided an Order ID or Email, you MUST use a tool IMMEDIATELY.
2. Tool Format: Action: tool_name(args). 
   Available: query_order(id_or_email), track_shipping(order_id), apply_refund(order_id).
3. If you just received an Observation from a tool, use that data to give a FINAL ANSWER to the user.
4. If ID is missing, ask for it.

Please provide your response (Thought + Action OR Final Answer):"""
        
        response_text, usage = self._call_llm(prompt)
        
        # Log to history
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response_text})
        
        return response_text, usage

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id: return "Error: case_id is required."
        try:
            if tool_name == "query_order": return self.simulator.query_order(case_id, tool_args)
            elif tool_name == "track_shipping": return self.simulator.track_shipping(case_id, tool_args)
            elif tool_name == "apply_refund": return self.simulator.apply_refund(case_id, tool_args)
            else: return f"Error: Tool {tool_name} not found."
        except Exception as e:
            return f"Error executing tool: {str(e)}"
