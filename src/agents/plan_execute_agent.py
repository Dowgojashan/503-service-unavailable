import re
from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class PlanExecuteAgent(BaseAgent):
    def __init__(self, model_name="llama3.1:8b", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        self.history.append({"role": "user", "content": user_input})
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Step 1: Planning (Strict Constraint: No prediction)
        plan_prompt = f"""Based on the dialogue history: {[h['content'] for h in self.history if h['role'] == 'user']}

Check for any Order ID (ORDxxx) or Email mentioned in the history.

Create a multi-step plan to resolve this request. 

If Order ID/Email is present in history, include using query_order tool FIRST to get data.
If no ID/Email in history, include asking the user for it as the first step.

List ONLY the steps. DO NOT predict tool results or assume data exists."""
        plan, usage = self._call_llm(plan_prompt)
        for k in total_usage: total_usage[k] += usage[k]
        full_trace = f"--- Plan ---\n{plan}"
        
        # Step 2: Execution
        current_context = f"Plan: {plan}\nNow execute the plan step by step. For each step that requires data, use the appropriate tool. If you need order details, you MUST use query_order with a valid ID from history. If no ID in history, ask the user. Provide a final response when done."
        for i in range(3): # Max 3 execution steps
            response, usage = self._call_llm(current_context)
            for k in total_usage: total_usage[k] += usage[k]
            
            # Catch meta-talk in internal steps
            if "(" in response or "waiting" in response.lower():
                 print("!!! [AGENT] Internal meta-talk detected. Cleaning response...")
                 response = re.sub(r"\(.*?\)", "", response).strip()

            full_trace += f"\n--- Execution Step {i+1} ---\n{response}"
            
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2).replace('"', '').replace("'", "").strip()
                # Validate tool_args - must not be None or empty
                if tool_args in ["None", "null", "", "''", '""']:
                    print("!!! [AGENT] Invalid tool args detected. Skipping tool call.")
                    continue
                observation = self._execute_tool(tool_name, tool_args, case_id)
                full_trace += f"\nObservation: {observation}\n"
                current_context += f"\n{response}\nObservation: {observation}\n"
            elif "ask the user" in response.lower() or "provide" in response.lower():
                # If asking for ID, stop execution
                break
            else:
                break
        
        # Final Step: Consolidate
        final_prompt = "Based on the plan and execution above, provide the Final Response to the user. If you used tools, base your response on the observations. If no tools were used and ID is missing, ask for it politely."
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
        if tool_name == "query_order": 
            return self.simulator.query_order(case_id, tool_args)
        elif tool_name == "track_shipping": 
            return self.simulator.track_shipping(case_id, tool_args)
        elif tool_name == "apply_refund": 
            return self.simulator.apply_refund(case_id, tool_args)
        elif tool_name == "cancel_order":
            return self.simulator.cancel_order(case_id, tool_args)
        return f"Error: Tool '{tool_name}' not found. Only query_order, track_shipping, apply_refund, cancel_order are allowed."
