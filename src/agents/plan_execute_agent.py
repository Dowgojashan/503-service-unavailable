import re
from src.agents.base import BaseAgent

class PlanExecuteAgent(BaseAgent):
    def __init__(self, model_name="llama3.1:8b", system_instruction=None):
        super().__init__(model_name, system_instruction)
        self.last_full_trace = ""

    def run(self, user_input, case_id=None):
        self.history.append({"role": "user", "content": user_input})
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        prompt = (
            "Follow the Plan-and-Execute protocol. "
            "Output your **Plan**, then under **Execution** write either:\n"
            "  Action: tool_name(param=\"value\")  ← then STOP immediately, or\n"
            "  Final Response: [message]  ← when no tool is needed.\n"
            "NEVER write Observation: yourself."
        )

        response, usage = self._call_llm(prompt)
        for k in total_usage:
            total_usage[k] += usage[k]

        self.last_full_trace = f"--- PlanExecute ---\n{response}"

        # If an Action: is present, return raw response so the runner can intercept the tool call.
        if re.search(r"Action:\s*\w+\s*\(", response):
            self.history.append({"role": "assistant", "content": response})
            return response, total_usage

        # Extract Final Response if present
        final_answer = response
        if "Final Response:" in response:
            final_answer = response.split("Final Response:")[-1].strip()

        # Remove plan/execution headers from the customer-facing answer
        header_prefixes = ["**plan**", "**execution**", "plan:", "execution:", "current step:"]
        clean_lines = [
            line for line in final_answer.split("\n")
            if not any(line.strip().lower().startswith(p) for p in header_prefixes)
        ]
        final_answer = "\n".join(clean_lines).strip()

        if not final_answer:
            last_lines = [l.strip() for l in response.strip().split("\n") if l.strip()]
            final_answer = last_lines[-1] if last_lines else "How can I assist you?"

        self.history.append({"role": "assistant", "content": final_answer})
        return final_answer, total_usage
