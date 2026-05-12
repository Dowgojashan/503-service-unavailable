from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator
import re

class ReflectionAgent(BaseAgent):
    def __init__(self, model_name="gemini-1.5-flash", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        # Step 1: Initial Generation & Tool use (if needed)
        # For simplicity, we use a ReAct-like loop for tool access, 
        # but we force a reflection step before the final answer.
        
        self.history.append({"role": "user", "content": user_input})
        
        # We'll use a specific prompt to trigger the Reflection pattern
        prompt = f"User Input: {user_input}\nPlease follow the Reflection pattern: Initial Draft -> Reflection -> Final Response."
        
        response = self._call_llm(prompt)
        print(f"--- Reflection Process ---\n{response}")
        
        # Check for tool use in the initial draft or reflection
        # (This agent is a bit more 'all-in-one' for this implementation)
        action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
        if action_match:
            tool_name = action_match.group(1)
            tool_args = action_match.group(2).replace('"', '').replace("'", "").strip()
            observation = self._execute_tool(tool_name, tool_args, case_id)
            
            # Refinement based on tool observation
            refine_prompt = f"{prompt}\n{response}\nObservation: {observation}\nNow provide the Final Response based on this observation."
            response = self._call_llm(refine_prompt)
            
        if "Final Response:" in response:
            final_answer = response.split("Final Response:")[1].strip()
        else:
            final_answer = response
            
        self.history.append({"role": "assistant", "content": response})
        return final_answer

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id: return "Error: case_id is required."
        if tool_name == "query_order": return self.simulator.query_order(case_id, tool_args)
        elif tool_name == "track_shipping": return self.simulator.track_shipping(case_id, tool_args)
        elif tool_name == "apply_refund": return self.simulator.apply_refund(case_id, tool_args)
        return f"Error: Tool {tool_name} not found."
