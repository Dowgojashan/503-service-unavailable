"""
ReAct Agent (Reasoning and Acting) — Architecture 2.

Interleaves Thought (internal reasoning) and Action (tool invocation) in each turn.
The runner injects Observations after each Action, up to max_iterations=5.
Loop control and hallucination guards are handled externally in src/core/runner.py.
"""

import re
from src.agents.base import BaseAgent
from src.tools.simulator import ToolSimulator

class ReActAgent(BaseAgent):
    def __init__(self, model_name="llama3.1:8b", system_instruction=None, max_iterations=5):
        super().__init__(model_name, system_instruction)
        self.simulator = ToolSimulator()
        self.max_iterations = max_iterations

    @staticmethod
    def _parse_tool_args(tool_args_raw):
        order_match = re.search(r'(?:order_id\s*=\s*)?["\']?(ORD[\w]+)["\']?', tool_args_raw)
        order_id = order_match.group(1) if order_match else tool_args_raw.strip().strip('"').strip("'")
        reason_match = re.search(r'reason\s*=\s*["\']([^"\']+)["\']', tool_args_raw)
        reason = reason_match.group(1) if reason_match else "Customer request"
        return order_id, reason

    def run(self, user_input, case_id=None):
        self.history.append({"role": "user", "content": user_input})

        current_prompt = (
            "Please proceed with your next Thought and either Action or Final Answer.\n"
            "REMINDER: Use plain text tags — write 'Thought:' not '**Thought:**'. "
            "No bold markers on structural tags. Stop immediately after any Action: line."
        )
        
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
        
        # [NEW] Relaxed Parser for Farewell/Completion
        # If the response doesn't have tags but looks like a polite ending, we allow it
        farewell_keywords = ["thank you", "bye", "goodbye", "have a nice day", "have a wonderful day", "welcome", "assist you"]
        has_tool_in_history = any("Observation:" in h['content'] for h in self.history if h['role'] == 'user')
        
        if not "Action:" in response and (any(kw in response.lower() for kw in farewell_keywords) or has_tool_in_history):
            print(">>> [AGENT] Tag-less response accepted as Final Answer (Relaxed Parser).")
            return response.strip(), total_usage
        
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
                order_id, reason = self._parse_tool_args(tool_args)
                return self.simulator.apply_refund(case_id, order_id, reason)
            elif tool_name == "cancel_order":
                order_id, reason = self._parse_tool_args(tool_args)
                return self.simulator.cancel_order(case_id, order_id, reason)
            else:
                return f"Error: Tool '{tool_name}' not found. Only query_order, track_shipping, apply_refund, cancel_order are allowed."
        except Exception as e:
            return f"Error executing tool: {str(e)}"
