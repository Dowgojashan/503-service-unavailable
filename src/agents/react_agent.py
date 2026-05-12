import re
from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class ReActAgent(BaseAgent):
    def __init__(self, model_name="gemini-2.5-flash", system_instruction=None, max_iterations=5):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()
        self.max_iterations = max_iterations

    def run(self, user_input, case_id=None):
        # Build context from history
        history_context = "\n".join([f"{h['role'].upper()}: {h['content']}" for h in self.history[-4:]])
        
        self.history.append({"role": "user", "content": user_input})
        
        current_prompt = f"Dialogue History:\n{history_context}\n\nUser Input: {user_input}\n"
        current_prompt += "\nREMINDER: identify the initial goal. If you have Order ID, use tools IMMEDIATELY. Once you have the Observation, you MUST proceed to next Thought or Final Answer."
        
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        full_trace = ""
        
        for i in range(self.max_iterations):
            response, usage = self._call_llm(current_prompt)
            # Check for API failure signal from BaseAgent
            if "SYSTEM_ERROR" in response:
                return response, usage 

            for k in total_usage: total_usage[k] += usage[k]
            full_trace += f"\n--- Step {i+1} ---\n{response}"
            
            # Parsing logic
            if "Final Answer:" in response:
                final_answer = response.split("Final Answer:")[1].strip()
                self.history.append({"role": "assistant", "content": full_trace})
                return final_answer, total_usage
            
            # Action Parsing (Robust Regex)
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2).replace('"', '').replace("'", "").strip()
                
                # Execute tool
                observation = self._execute_tool(tool_name, tool_args, case_id)
                observation_str = f"\nObservation: {observation}\n"
                full_trace += observation_str
                # Feed observation back into context for next iteration in the SAME turn
                current_prompt += f"\n{response}{observation_str}\nNext Thought:"
            else:
                # Fallback: if no action and no final answer, but maybe it's just formatting
                if i == self.max_iterations - 1:
                    self.history.append({"role": "assistant", "content": full_trace})
                    return response, total_usage
                current_prompt += f"\n{response}\nPlease continue your reasoning until you reach a Final Answer."

        return "ERROR: ReAct loop exceeded max iterations.", total_usage

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id:
            return "Error: case_id is required."
            
        try:
            if tool_name == "query_order":
                return self.simulator.query_order(case_id, tool_args)
            elif tool_name == "track_shipping":
                return self.simulator.track_shipping(case_id, tool_args)
            elif tool_name == "apply_refund":
                return self.simulator.apply_refund(case_id, tool_args)
            else:
                return f"Error: Tool {tool_name} not found."
        except Exception as e:
            return f"Error executing tool: {str(e)}"
