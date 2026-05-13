import os
import json
import re
import time
from datetime import datetime
from src.core.factory import AgentFactory
from src.agents.customer_agent import CustomerAgent

class DialogueRunner:
    def __init__(self, model_name="gemini-3.1-flash-lite"):
        self.model_name = model_name
        self.instructions_dir = "prompts/system_instructions"
        self.api_error_log = []  # Track API errors for diagnostics

    def _load_instruction(self, filename):
        path = os.path.join(self.instructions_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _extract_ids(self, text):
        """Helper to extract potential Order IDs or Emails from text."""
        order_ids = re.findall(r"ORD\d+", text)
        emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        return list(set(order_ids + emails))

    def run_conversation(self, case_id, fact_sheet, agent_type, persona_type, max_turns=6):
        """
        Runs a multi-turn conversation with ReAct Atomicity and State Protection.
        """
        # 1. Prepare Instructions
        common_instr = self._load_instruction("common.txt")
        persona_instr = self._load_instruction(f"persona_{persona_type.lower()}.txt")
        
        scaffold_map = {
            "ReAct": "react_scaffold.txt",
            "Reflection": "reflection_scaffold.txt",
            "PlanExecute": "plan_execute_scaffold.txt",
            "Single-slot": None
        }
        
        scaffold_instr = ""
        if scaffold_map.get(agent_type):
            scaffold_instr = self._load_instruction(scaffold_map[agent_type])
            
        service_instruction = f"{common_instr}\n\n{scaffold_instr}"
        
        # 2. Initialize Agents
        service_agent = AgentFactory.create_agent(
            agent_type=agent_type,
            model_name=self.model_name,
            system_instruction=service_instruction
        )
        
        customer_agent = CustomerAgent(
            model_name=self.model_name,
            persona_instruction=persona_instr,
            fact_sheet=fact_sheet
        )
        
        # 3. Dialogue Loop
        conversation_log = []
        last_service_response = None 
        task_resolved = False
        known_info = []
        response_history = []
        tool_triggered = False
        
        acc_usage = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "grand_total_tokens": 0
        }
        
        status = "IN_PROGRESS"
        
        print(f"\n>>> Case {case_id} | {agent_type} | {persona_type}")
        
        for turn_idx in range(max_turns):
            # --- TOKEN SAFETY VALVE ---
            if acc_usage["grand_total_tokens"] > 30000:
                print("!!! TOKEN SAFETY VALVE TRIGGERED")
                status = "FAILED_TOKEN_LIMIT"
                break

            turn_num = turn_idx + 1
            turn_data = {"turn": turn_num}
            
            # --- Customer Turn ---
            customer_msg, customer_usage = customer_agent.run(last_service_response)
            
            # Update tokens
            acc_usage["total_prompt_tokens"] += customer_usage["prompt_tokens"]
            acc_usage["total_completion_tokens"] += customer_usage["completion_tokens"]
            acc_usage["grand_total_tokens"] = acc_usage["total_prompt_tokens"] + acc_usage["total_completion_tokens"]

            if "SYSTEM_ERROR" in customer_msg:
                status = "SYSTEM_ERROR_CUSTOMER"
                break

            turn_data["customer"] = {"content": customer_msg, "usage": customer_usage}
            known_info.extend(self._extract_ids(customer_msg))
            known_info = list(set(known_info))
            
            print(f"[T{turn_num}][C]: {customer_msg}")
            
            if any(w in customer_msg.lower() for w in ["thank you", "bye"]) and task_resolved:
                conversation_log.append(turn_data)
                status = "SUCCESS"
                break
                
            # --- Service Agent Turn (Atomic ReAct Loop inside agent.run) ---
            info_str = ", ".join(known_info) if known_info else "None yet"
            agent_input = f"{customer_msg}\n\n[MANDATORY HINT]: Known info: {info_str}. If ID is present, you MUST use tools to provide the FINAL solution. Do NOT just say 'thank you' or 'how can I help'."
            
            service_final, service_usage = service_agent.run(agent_input, case_id=case_id)

            # --- [NEW] ReAct Execution Assertion ---
            # If the agent's Thought implies a lookup but no Action tag is provided, force it.
            if agent_type == "ReAct" and "Action:" not in service_final and "Final Answer:" in service_final:
                lower_final = service_final.lower()
                lookup_keywords = ["search", "query", "lookup", "check the status", "verify", "order details"]
                if any(kw in lower_final for kw in lookup_keywords):
                    print("!!! [EXECUTION ASSERTION] Agent mentioned lookup but missing Action tag. Retrying...")
                    error_prompt = "Error: You mentioned a lookup in your Thought but did not provide a valid Action tag. Please provide the Action tag now to get real data."
                    service_final, next_usage = service_agent.run(error_prompt, case_id=case_id)
                    for k in service_usage: service_usage[k] += next_usage[k]

            # --- [NEW] ReAct Mode Observation Injection (Closed-Loop) ---
            # If the agent returned a tool call, we loop until we get a non-tool-call final response
            while agent_type == "Reflection" and "[Tool Call:" in service_final:
                match = re.search(r"\[Tool Call:\s*(\w+)\s*\((.*?)\)\]", service_final)
                if match:
                    # [Improved Parsing] Extract value from "key=value" or just "value"
                    if "=" in tool_args:
                        # Extract everything after the first "="
                        tool_args = tool_args.split("=", 1)[1].strip()
                    
                    print(f"--- [RUNNER INTERCEPT] Executing: {tool_name}({tool_args}) ---")
                    
                    # 1. Execute tool
                    observation = service_agent._execute_tool(tool_name, tool_args, case_id)
                    
                    # 2. Inject Observation into Agent history
                    obs_prompt = f"Observation: {observation}"
                    print(f"--- [RUNNER INJECT] Observation: {observation} ---")
                    
                    # 3. Re-trigger Agent to process the observation
                    service_final, next_usage = service_agent.run(obs_prompt, case_id=case_id)
                    
                    # Merge token usage
                    for k in service_usage: service_usage[k] += next_usage[k]
                else:
                    break # Safety break if regex fails despite tag presence

            # --- [NEW] ReAct Mode Observation Injection (Closed-Loop) ---
            while agent_type == "ReAct" and "Action:" in service_final:
                # [Action Truncation] Ensure we don't process hallucinated Observations
                if "Observation:" in service_final:
                    service_final = service_final.split("Observation:")[0].strip()
                
                match = re.search(r"Action:\s*(\w+)\((.*?)\)", service_final)
                if match:
                    tool_name = match.group(1)
                    tool_args = match.group(2).replace('"', '').replace("'", "").strip()
                    
                    # [Improved Parsing] Extract value from "key=value" or just "value"
                    if "=" in tool_args:
                        tool_args = tool_args.split("=", 1)[1].strip()
                    
                    print(f"--- [RE-ACT INTERCEPT] Executing: {tool_name}({tool_args}) ---")
                    
                    # 1. Execute tool
                    observation = service_agent._execute_tool(tool_name, tool_args, case_id)
                    
                    # 2. Inject Observation into Agent history
                    obs_prompt = f"Observation: {observation}"
                    print(f"--- [RE-ACT INJECT] Observation: {observation} ---")
                    
                    # 3. Re-trigger Agent to process the observation
                    service_final, next_usage = service_agent.run(obs_prompt, case_id=case_id)
                    
                    # Merge token usage
                    for k in service_usage: service_usage[k] += next_usage[k]
                else:
                    break 

            # --- [CRITICAL] Thought Leakage Block (The Ultimate Defense) ---
            # 1. Prioritize content after the final answer labels
            if "Final Response:" in service_final:
                service_final = service_final.split("Final Response:")[-1].strip()
            elif "Final Answer:" in service_final:
                service_final = service_final.split("Final Answer:")[-1].strip()
            
            # 2. Scan line by line and remove all lines containing thought labels (Destructive Cleanup)
            lines = service_final.split("\n")
            clean_lines = []
            forbidden_tokens = [
                "Initial Draft", "Reflection", "Draft:", "Observation:", "Action:", "Final Response:", "Final Answer:",
                "Verification", "Goal Anchoring", "Fact Check", "Policy Check", "Tone Check", "Security Check",
                "Action Integrity", "[Tool Call:", "Thought:"
            ]
            for line in lines:
                if not any(token.lower() in line.lower() for token in forbidden_tokens):
                    clean_lines.append(line)
            service_final = "\n".join(clean_lines).strip()

            # 3. If cleaning results in an empty string (meaning the entire output was thoughts), 
            # fallback to the last segment of the original output that doesn't look like a thought.
            if not service_final:
                 # Try to find something that doesn't look like a thought
                 for line in reversed(lines):
                     if not any(token.lower() in line.lower() for token in forbidden_tokens) and line.strip():
                         service_final = line.strip()
                         break
                 if not service_final:
                     service_final = lines[-1].strip()

            # Update tokens (includes all internal ReAct iterations)
            acc_usage["total_prompt_tokens"] += service_usage["prompt_tokens"]
            acc_usage["total_completion_tokens"] += service_usage["completion_tokens"]
            acc_usage["grand_total_tokens"] = acc_usage["total_prompt_tokens"] + acc_usage["total_completion_tokens"]

            if "SYSTEM_ERROR" in service_final:
                print(f"!!! SYSTEM ERROR ENCOUNTERED IN AGENT: {service_final}")
                status = "SYSTEM_ERROR_AGENT"
                # Store whatever trace we have before exiting
                full_trace = service_agent.history[-1]["content"] if service_agent.history else "No trace"
                turn_data["service_agent"] = {"final_answer": "ERROR", "full_trace": full_trace, "usage": service_usage}
                conversation_log.append(turn_data)
                break

            # Loop Detection
            if service_final in response_history[-2:]:
                status = "LOOP_FAILURE"
                break
            response_history.append(service_final)

            # --- Task Completion Check (Reliability Update) ---
            full_trace = service_agent.history[-1]["content"]
            # Only count as tool triggered if "Observation:" is followed by a non-error JSON
            if "Observation:" in full_trace and any(ok in full_trace for ok in ["'status': 'success'", '"status": "success"']):
                tool_triggered = True
                # Success requires both tool trigger AND a meaningful response based on it
                if any(k in service_final.lower() for k in ["cancel", "refund", "status", "date", "shipped", "delivered", "eligible"]):
                    task_resolved = True

            if agent_type == "Single-slot" and any(k in service_final.lower() for k in ["cancel", "refunded", "status is", "order number"]):
                task_resolved = True
                tool_triggered = True 
 

            turn_data["service_agent"] = {
                "final_answer": service_final,
                "full_trace": full_trace,
                "usage": service_usage
            }
            print(f"[T{turn_num}][A]: {service_final}")
            
            conversation_log.append(turn_data)
            last_service_response = service_final
            
            if any(w in service_final.lower() for w in ["have a nice day", "goodbye"]) and task_resolved:
                 status = "SUCCESS"
                 break
        
        if status == "IN_PROGRESS":
            status = "SUCCESS" if task_resolved else "FAILED_INCOMPLETE"

        # 4. Save Logs
        log_data = {
            "metadata": {
                "case_id": case_id, "agent_type": agent_type, "persona_type": persona_type,
                "model": self.model_name, "status": status, "task_status": "TOOL_TRIGGERED" if tool_triggered else "NO_TOOL"
            },
            "usage_summary": acc_usage,
            "conversation": conversation_log
        }
        
        os.makedirs("outputs/logs", exist_ok=True)
        log_path = f"outputs/logs/log_{case_id}_{agent_type}_{persona_type}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
            
        print(f">>> Finished with Status: {status}. Saved to {log_path}\n")
        return log_data

if __name__ == "__main__":
    with open("data/fact_sheets.json", "r", encoding="utf-8") as f:
        all_facts = json.load(f)
    runner = DialogueRunner()
    runner.run_conversation("CASE_001", all_facts["CASE_001"], "ReAct", "Polite")
