import re
from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class PlanExecuteAgent(BaseAgent):
    def __init__(self, model_name="gemini-1.5-flash", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        self.history.append({"role": "user", "content": user_input})
        
        # Step 1: Planning
        plan_prompt = f"User Input: {user_input}\nPlease create a multi-step plan to resolve this request. List the steps clearly."
        plan = self._call_llm(plan_prompt)
        print(f"--- Plan ---\n{plan}")
        
        # Step 2: Execution
        # We pass the plan to the executor
        execution_prompt = f"User Input: {user_input}\nPlan: {plan}\nNow execute the plan. Use tools if necessary. Provide a final response."
        
        # For simplicity, we'll allow one round of execution which can include multiple tool calls if the model supports it 
        # or we can loop. Let's do a simple loop for execution steps.
        
        current_context = execution_prompt
        for i in range(3): # Max 3 execution steps
            response = self._call_llm(current_context)
            print(f"--- Execution Step {i+1} ---\n{response}")
            
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2).replace('"', '').replace("'", "").strip()
                observation = self._execute_tool(tool_name, tool_args, case_id)
                current_context += f"\n{response}\nObservation: {observation}\n"
            else:
                break
        
        # Final Step: Consolidate
        final_prompt = f"{current_context}\nBased on the plan and execution above, provide the Final Response to the user."
        final_answer = self._call_llm(final_prompt)
        
        if "Final Response:" in final_answer:
            final_answer = final_answer.split("Final Response:")[1].strip()
            
        self.history.append({"role": "assistant", "content": final_answer})
        return final_answer

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id: return "Error: case_id is required."
        if tool_name == "query_order": return self.simulator.query_order(case_id, tool_args)
        elif tool_name == "track_shipping": return self.simulator.track_shipping(case_id, tool_args)
        elif tool_name == "apply_refund": return self.simulator.apply_refund(case_id, tool_args)
        return f"Error: Tool {tool_name} not found."
