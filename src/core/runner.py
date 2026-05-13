import os
import json
import re
import time
from datetime import datetime
from src.core.factory import AgentFactory
from src.agents.customer_agent import CustomerAgent

class DialogueRunner:
    def __init__(self, model_name="gemma-4-31b-it"):
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
        last_service_response = "" 
        task_resolved = False
        tool_triggered = False
        known_info = []
        response_history = []
        
        acc_usage = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "grand_total_tokens": 0
        }
        
        status = "IN_PROGRESS"
        final_resolution = "PENDING"

        def is_farewell(text):
            if not text: return False
            farewell_keywords = ["thank you", "bye", "goodbye", "have a nice day", "have a wonderful day", "that is all", "that's all", "i understand"]
            return any(w in text.lower() for w in farewell_keywords)
        
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
            # Extract IDs from the latest message
            new_ids = self._extract_ids(customer_msg)
            known_info.extend(new_ids)
            known_info = list(set(known_info))
            
            print(f"[T{turn_num}][C]: {customer_msg}")
            
            # --- Termination Check (Customer side) ---
            # If customer says goodbye and we have a resolution
            # [REFINED]: Prohibition on termination if a NEW ID was just provided in this turn
            if is_farewell(customer_msg) and task_resolved and not new_ids:
                print(">>> [TERMINATION] Customer signaled end of conversation.")
                conversation_log.append(turn_data)
                status = "SUCCESS"
                break
                
            # --- Service Agent Turn (Atomic Loop) ---
            info_str = ", ".join(known_info) if known_info else "None yet"
            agent_input = f"{customer_msg}\n\n[MANDATORY HINT]: Known info: {info_str}. If ID is present, you MUST use tools to provide the FINAL solution. Do NOT just say 'thank you' or 'how can I help'."
            
            service_final, service_usage = service_agent.run(agent_input, case_id=case_id)

            # --- [NEW] Reflection Mode Atomic Loop (Multi-stage internal loop) ---
            # If Reflection mode is active, we loop internally until we get a Final Response
            reflection_iter = 0
            while agent_type == "Reflection" and reflection_iter < 3:
                reflection_iter += 1
                
                # Case A: Tool Call detected
                if "[Tool Call:" in service_final:
                    # [OPTIMIZATION] Check if conversation is already resolved
                    if task_resolved and is_farewell(customer_msg):
                        print(">>> [RUNNER] Task already resolved and customer said goodbye. Blocking redundant tool call.")
                        service_final = "Thank you for your patience. Have a great day! (System: Tool call blocked for resolved case)"
                        break

                    match = re.search(r"\[Tool Call:\s*(\w+)\s*\((.*?)\)\]", service_final)
                    if match:
                        tool_name = match.group(1)
                        tool_args = match.group(2).replace('"', '').replace("'", "").strip()
                        if "=" in tool_args: tool_args = tool_args.split("=", 1)[1].strip()
                        
                        print(f"--- [RUNNER INTERCEPT] Executing: {tool_name}({tool_args}) ---")
                        observation = service_agent._execute_tool(tool_name, tool_args, case_id)
                        
                        # Inject Observation with explicit instruction to finish reflection
                        obs_prompt = f"Observation: {observation}\n\n[SYSTEM]: You have received the data. Please proceed to Reflection and provide the Final Response now."
                        print(f"--- [RUNNER INJECT] Observation: {observation} ---")
                        
                        service_final, next_usage = service_agent.run(obs_prompt, case_id=case_id)
                        for k in service_usage: service_usage[k] += next_usage[k]
                    else: break
                
                # Case B: Incomplete Reflection (No Tool Call AND No Final Response)
                elif "Final Response:" not in service_final:
                    print(f"!!! [RUNNER] Incomplete Reflection detected. Retrying iteration {reflection_iter}...")
                    
                    # [NEW] Force switch to Single-slot fallback if retries exhausted
                    if reflection_iter >= 3:
                        print("!!! [RUNNER] Reflection retries exhausted. Force-switching to Single-slot logic for this turn.")
                        fallback_prompt = f"Dialogue Context: {customer_msg}\n\nPlease provide a final, polite response to the user without any internal headers."
                        service_final, next_usage = service_agent._call_llm(fallback_prompt) # Direct LLM call
                        for k in service_usage: service_usage[k] += next_usage[k]
                        break

                    retry_prompt = "[SYSTEM]: You stopped early without a Final Response or a Tool Call. Please finish your reflection and provide the Final Response now."
                    service_final, next_usage = service_agent.run(retry_prompt, case_id=case_id)
                    for k in service_usage: service_usage[k] += next_usage[k]
                
                else:
                    # We have a Final Response, we can break the loop
                    break

            # --- [NEW] ReAct Mode Observation Injection (Closed-Loop) ---
            while agent_type == "ReAct" and "Action:" in service_final:
                if "Observation:" in service_final:
                    service_final = service_final.split("Observation:")[0].strip()
                match = re.search(r"Action:\s*(\w+)\((.*?)\)", service_final)
                if match:
                    tool_name = match.group(1)
                    tool_args = match.group(2).replace('"', '').replace("'", "").strip()
                    if "=" in tool_args: tool_args = tool_args.split("=", 1)[1].strip()
                    print(f"--- [RE-ACT INTERCEPT] Executing: {tool_name}({tool_args}) ---")
                    # Single-slot doesn't have _execute_tool natively but Factory/Base could handle it?
                    # Actually ReActAgent has it. Let's make sure SingleSlotAgent can also execute tools.
                    if hasattr(service_agent, "_execute_tool"):
                        observation = service_agent._execute_tool(tool_name, tool_args, case_id)
                    else:
                        # Fallback if _execute_tool is missing (should probably move to base)
                        from src.tools.simulator import ToolSimulator
                        sim = ToolSimulator()
                        if tool_name == "query_order": observation = sim.query_order(case_id, tool_args)
                        elif tool_name == "track_shipping": observation = sim.track_shipping(case_id, tool_args)
                        elif tool_name == "apply_refund": observation = sim.apply_refund(case_id, tool_args)
                        else: observation = f"Error: Tool {tool_name} not found."
                    
                    obs_prompt = f"Observation: {observation}"
                    service_final, next_usage = service_agent.run(obs_prompt, case_id=case_id)
                    for k in service_usage: service_usage[k] += next_usage[k]
                else:
                    break

            # --- [CRITICAL] Thought Leakage Block ---
            if "Final Response:" in service_final:
                service_final = service_final.split("Final Response:")[-1].strip()
            elif "Final Answer:" in service_final:
                service_final = service_final.split("Final Answer:")[-1].strip()
            
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

            if not service_final:
                 for line in reversed(lines):
                     if not any(token.lower() in line.lower() for token in forbidden_tokens) and line.strip():
                         service_final = line.strip()
                         break
                 if not service_final:
                     service_final = lines[-1].strip()

            acc_usage["total_prompt_tokens"] += service_usage["prompt_tokens"]
            acc_usage["total_completion_tokens"] += service_usage["completion_tokens"]
            acc_usage["grand_total_tokens"] = acc_usage["total_prompt_tokens"] + acc_usage["total_completion_tokens"]

            if "SYSTEM_ERROR" in service_final:
                status = "SYSTEM_ERROR_AGENT"
                full_trace = service_agent.history[-1]["content"] if service_agent.history else "No trace"
                turn_data["service_agent"] = {"final_answer": "ERROR", "full_trace": full_trace, "usage": service_usage}
                conversation_log.append(turn_data)
                break

            if service_final in response_history[-2:]:
                status = "LOOP_FAILURE"
                break
            response_history.append(service_final)

            # --- Task Completion Check ---
            full_trace = service_agent.history[-1]["content"]
            if "Observation:" in full_trace and any(ok in full_trace for ok in ["'status': 'success'", '"status": "success"']):
                tool_triggered = True
                refusal_keywords = ["cannot", "unable", "shipped", "policy", "unfortunately", "no longer eligible", "outside the return window"]
                fulfilled_keywords = ["cancel", "refund", "status", "date", "shipped", "delivered", "eligible"]
                if any(k in service_final.lower() for k in refusal_keywords):
                    task_resolved = True
                    final_resolution = "REFUSED_BY_POLICY"
                elif any(k in service_final.lower() for k in fulfilled_keywords):
                    task_resolved = True
                    final_resolution = "EXECUTED_SUCCESSFULLY"

            if agent_type == "Single-slot" and any(k in service_final.lower() for k in ["cancel", "refunded", "status is", "order number"]):
                task_resolved = True
                tool_triggered = True 
                final_resolution = "EXECUTED_SUCCESSFULLY"

            turn_data["service_agent"] = {
                "final_answer": service_final,
                "full_trace": full_trace,
                "usage": service_usage
            }
            print(f"[T{turn_num}][A]: {service_final}")
            conversation_log.append(turn_data)
            last_service_response = service_final
            
            # --- Termination Check (Service Agent side) ---
            if is_farewell(service_final) and task_resolved:
                 print(">>> [TERMINATION] Agent signaled end of conversation.")
                 status = "SUCCESS"
                 break
        
        if status == "IN_PROGRESS":
            status = "SUCCESS" if task_resolved else "FAILED_INCOMPLETE"

        # --- FINAL INTEGRITY CHECK ---
        if status == "SUCCESS" and not tool_triggered:
             print("!!! [INTEGRITY CHECK] Success detected without tool trigger. Downgrading...")
             status = "FAILED_INCOMPLETE (No Tool Triggered)"

        # 4. Save Logs
        log_data = {
            "metadata": {
                "case_id": case_id, "agent_type": agent_type, "persona_type": persona_type,
                "model": self.model_name, "status": status, 
                "task_status": "TOOL_TRIGGERED" if tool_triggered else "NO_TOOL",
                "final_resolution": final_resolution
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
    runner.run_conversation("CASE_001", all_facts["CASE_001"], "Reflection", "Polite")
