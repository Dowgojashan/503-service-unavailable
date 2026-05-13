from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator
import re

class ReflectionAgent(BaseAgent):
    def __init__(self, model_name="gemini-3.1-flash-lite", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()

    def run(self, user_input, case_id=None):
        # 1. Update History
        # If user_input starts with "Observation:", it's a tool result injection
        if user_input.startswith("Observation:"):
             self.history.append({"role": "user", "content": user_input})
        else:
             self.history.append({"role": "user", "content": user_input})

        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # 2. Build context from history
        # We include previous turns to ensure the agent remembers the context and tool results
        history_context = ""
        for h in self.history[-6:]:
            role = h['role'].upper()
            content = h['content']
            # Clean up content for the prompt to avoid confusing the agent with its own internal traces
            if role == "ASSISTANT" and "Final Response:" in content:
                 # Extract only the Final Response for history context to keep it clean
                 # but keep the full trace in self.history
                 clean_content = content.split("Final Response:")[-1].strip()
                 history_context += f"{role}: {clean_content}\n"
            else:
                 history_context += f"{role}: {content}\n"

        # 3. Reflection Process
        prompt = f"Dialogue History:\n{history_context}\n\nPlease follow the Reflection pattern: Initial Draft -> Reflection -> Final Response."
        response, usage = self._call_llm(prompt)
        for k in total_usage: total_usage[k] += usage[k]
        
        # [ROBUSTNESS] Check for empty or header-only response
        if len(response.strip()) < 50 or "Final Response:" not in response:
             if "[Tool Call:" not in response:
                 print("!!! Incomplete Reflection detected. Retrying with explicit instruction...")
                 retry_prompt = f"{prompt}\n\nIMPORTANT: You MUST complete the process and provide a 'Final Response:' section. Do NOT stop after the headers."
                 response, next_usage = self._call_llm(retry_prompt)
                 for k in total_usage: total_usage[k] += next_usage[k]

        full_trace = f"--- Reflection Process ---\n{response}"
        
        # Check if this response contains a Tool Call
        # If it does, we return the RAW response (including headers) so the runner can intercept it
        # The runner will handle the Observation injection
        if "[Tool Call:" in response:
            self.history.append({"role": "assistant", "content": full_trace})
            return response, total_usage

        # If no tool call, extract the Final Response correctly
        final_answer = response
        if "Final Response:" in response:
            parts = response.split("Final Response:")
            final_answer = parts[-1].strip()
        
        # Cleanup internal thoughts for the customer
        cleanup_patterns = [
            r"Initial Draft:.*",
            r"Reflection:.*",
            r"\*\*Initial Draft\*\*:.*",
            r"\*\*Reflection\*\*:.*",
            r"\*\*Final Response\*\*:",
            r"Action:.*",
            r"Observation:.*"
        ]
        for pattern in cleanup_patterns:
            final_answer = re.sub(pattern, "", final_answer, flags=re.IGNORECASE | re.DOTALL).strip()
            
        if not final_answer:
            lines = [l for l in response.split("\n") if l.strip()]
            if lines: final_answer = lines[-1].strip()

        self.history.append({"role": "assistant", "content": full_trace})
        return final_answer, total_usage

    def _execute_tool(self, tool_name, tool_args, case_id):
        if not case_id: return "Error: case_id is required."
        if tool_name == "query_order": return self.simulator.query_order(case_id, tool_args)
        elif tool_name == "track_shipping": return self.simulator.track_shipping(case_id, tool_args)
        elif tool_name == "apply_refund": return self.simulator.apply_refund(case_id, tool_args)
        return f"Error: Tool {tool_name} not found."
