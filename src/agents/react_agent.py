import re
from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class ReActAgent(BaseAgent):
    def __init__(self, model_name="gemini-1.5-flash", system_instruction=None, max_iterations=5):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()
        self.max_iterations = max_iterations

    def run(self, user_input, case_id=None):
        self.history.append({"role": "user", "content": user_input})
        
        current_prompt = f"User Input: {user_input}\n"
        
        for i in range(self.max_iterations):
            response = self._call_llm(current_prompt)
            print(f"--- Iteration {i+1} ---\n{response}") # For debugging
            
            # Check for Final Answer
            if "Final Answer:" in response:
                final_answer = response.split("Final Answer:")[1].strip()
                self.history.append({"role": "assistant", "content": response})
                return final_answer
            
            # Parse Action
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", response)
            if action_match:
                tool_name = action_match.group(1)
                tool_args = action_match.group(2).replace('"', '').replace("'", "").strip()
                
                # Execute tool
                observation = self._execute_tool(tool_name, tool_args, case_id)
                current_prompt += f"\n{response}\nObservation: {observation}\n"
            else:
                # If no action found but not final answer, just return the response
                self.history.append({"role": "assistant", "content": response})
                return response

        return "I'm sorry, I couldn't resolve your request within the maximum number of steps."

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id:
            return "Error: case_id is required to use tools."
            
        if tool_name == "query_order":
            return self.simulator.query_order(case_id, tool_args)
        elif tool_name == "track_shipping":
            return self.simulator.track_shipping(case_id, tool_args)
        elif tool_name == "apply_refund":
            return self.simulator.apply_refund(case_id, tool_args)
        else:
            return f"Error: Tool {tool_name} not found."
