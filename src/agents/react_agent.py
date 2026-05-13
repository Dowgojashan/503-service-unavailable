import re
from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class ReActAgent(BaseAgent):
    def __init__(self, model_name="gemini-3.1-flash-lite", system_instruction=None, max_iterations=5):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()
        self.max_iterations = max_iterations

    def run(self, user_input, case_id=None):
        # 1. Update History
        # If user_input starts with "Observation:", it's a tool result injection from the runner
        self.history.append({"role": "user", "content": user_input})
        
        # 2. Build context from history
        # Include enough context for the agent to follow the reasoning chain
        history_context = ""
        for h in self.history[-8:]:
            role = h['role'].upper()
            content = h['content']
            # If it's the assistant, we might want to clean up internal thoughts for the prompt context
            # but for ReAct, thoughts are often part of the context.
            # However, we'll keep it simple for now.
            history_context += f"{role}: {content}\n"
        
        current_prompt = f"Dialogue History:\n{history_context}\n\nPlease proceed with your next Thought and either Action or Final Answer."
        
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Single LLM call approach - Loop control is now in runner.py
        response, usage = self._call_llm(current_prompt)
        for k in total_usage: total_usage[k] += usage[k]
        
        # Check for API failure
        if "SYSTEM_ERROR" in response:
            return response, usage 

        # Parsing and Truncation (Internal safety)
        # If the model hallucinates an Observation after Action, we cut it off here too
        if "Action:" in response:
            lines = response.split("\n")
            truncated_lines = []
            for line in lines:
                truncated_lines.append(line)
                if "Action:" in line:
                    break
            response = "\n".join(truncated_lines)

        self.history.append({"role": "assistant", "content": response})
        
        # Extraction logic
        if "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[1].strip()
            return final_answer, total_usage
        
        # If it's an Action, we return the whole thing so the runner can parse it
        return response, total_usage

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
