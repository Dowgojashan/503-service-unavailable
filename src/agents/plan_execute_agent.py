import re
from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class PlanExecuteAgent(BaseAgent):
    def __init__(self, model_name="gemini-3.1-flash-lite", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        self.history.append({"role": "user", "content": user_input})
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Step 1: Planning
        plan_prompt = f"User Input: {user_input}\nPlease create a multi-step plan to resolve this request. List the steps clearly."
        plan, usage = self._call_llm(plan_prompt)
        for k in total_usage: total_usage[k] += usage[k]
        full_trace = f"--- Plan ---\n{plan}"
        
        # Step 2: Execution
        current_context = f"User Input: {user_input}\nPlan: {plan}\nNow execute the plan. Use tools if necessary. Provide a final response."
        for i in range(3): # Max 3 execution steps
            response, usage = self._call_llm(current_context)
            for k in total_usage: total_usage[k] += usage[k]
            full_trace += f"\n--- Execution Step {i+1} ---\n{response}"
            
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2).replace('"', '').replace("'", "").strip()
                observation = self._execute_tool(tool_name, tool_args, case_id)
                full_trace += f"\nObservation: {observation}\n"
                current_context += f"\n{response}\nObservation: {observation}\n"
            else:
                break
        
        # Final Step: Consolidate
        final_prompt = f"{current_context}\nBased on the plan and execution above, provide the Final Response to the user."
        final_answer, usage = self._call_llm(final_prompt)
        for k in total_usage: total_usage[k] += usage[k]
        
        if "Final Response:" in final_answer:
            final_result = final_answer.split("Final Response:")[1].strip()
        else:
            final_result = final_answer
            
        self.history.append({"role": "assistant", "content": full_trace})
        return final_result, total_usage

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id: return "Error: case_id is required."
        if tool_name == "query_order": return self.simulator.query_order(case_id, tool_args)
        elif tool_name == "track_shipping": return self.simulator.track_shipping(case_id, tool_args)
        elif tool_name == "apply_refund": return self.simulator.apply_refund(case_id, tool_args)
        return f"Error: Tool {tool_name} not found."
