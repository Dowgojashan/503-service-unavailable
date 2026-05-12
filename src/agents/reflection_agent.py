from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator
import re

class ReflectionAgent(BaseAgent):
    def __init__(self, model_name="gemini-2.5-flash", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        self.history.append({"role": "user", "content": user_input})
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Step 1: Reflection Process
        prompt = f"User Input: {user_input}\nPlease follow the Reflection pattern: Initial Draft -> Reflection -> Final Response."
        response, usage = self._call_llm(prompt)
        for k in total_usage: total_usage[k] += usage[k]
        
        full_trace = f"--- Reflection Process ---\n{response}"
        
        # Check for tool use
        action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
        if action_match:
            tool_name = action_match.group(1)
            tool_args = action_match.group(2).replace('"', '').replace("'", "").strip()
            observation = self._execute_tool(tool_name, tool_args, case_id)
            full_trace += f"\nObservation: {observation}\n"
            
            # Refinement
            refine_prompt = f"{prompt}\n{response}\nObservation: {observation}\nNow provide the Final Response based on this observation."
            response, usage = self._call_llm(refine_prompt)
            for k in total_usage: total_usage[k] += usage[k]
            full_trace += f"\n--- Final Refinement ---\n{response}"
            
        if "Final Response:" in response:
            final_answer = response.split("Final Response:")[1].strip()
        else:
            final_answer = response # Fallback
            
        self.history.append({"role": "assistant", "content": full_trace})
        return final_answer, total_usage

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id: return "Error: case_id is required."
        if tool_name == "query_order": return self.simulator.query_order(case_id, tool_args)
        elif tool_name == "track_shipping": return self.simulator.track_shipping(case_id, tool_args)
        elif tool_name == "apply_refund": return self.simulator.apply_refund(case_id, tool_args)
        return f"Error: Tool {tool_name} not found."
