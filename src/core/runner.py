import os
import json
import re
import time
from datetime import datetime
from src.core.factory import AgentFactory
from src.agents.customer_agent import CustomerAgent

class DialogueRunner:
    def __init__(self, model_name="llama3.1:8b"):
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

    @staticmethod
    def _parse_order_action_args(tool_args_raw):
        """
        Robustly extract (order_id, reason) from tool arg strings like:
          order_id="ORD60227680", reason="Customer request"
          ORD60227680, reason="Customer request"
          ORD60227680
        Returns (order_id_str_or_None, reason_str).
        """
        order_match = re.search(r'(?:order_id\s*=\s*)?["\']?(ORD[\w]+)["\']?', tool_args_raw)
        order_id = order_match.group(1) if order_match else None

        reason_match = re.search(r'reason\s*=\s*["\']([^"\']+)["\']', tool_args_raw)
        reason = reason_match.group(1) if reason_match else "Customer request"

        return order_id, reason

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
        query_verified = False   # True once query_order returns success
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
            farewell_keywords = [
                "thank you", "bye", "goodbye", "have a nice day", "have a wonderful day",
                "that is all", "that's all", "i understand",
                "conversation is now closed", "matter is now closed", "case is now closed",
                "have a great day", "have a good day", "take care",
                "is there anything else i can help", "feel free to reach out",
            ]
            return any(w in text.lower() for w in farewell_keywords)
        
        print(f"\n>>> Case {case_id} | {agent_type} | {persona_type}")
        
        for turn_idx in range(max_turns):
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
            if not known_info:
                sys_hint = (
                    "[SYSTEM CONTEXT — INTERNAL]: No Order ID or Email detected yet. "
                    "Ask the customer for their Order ID (ORDxxx format) or registered email. Nothing else."
                )
            elif not query_verified:
                # ID present but order not yet queried — force query_order
                sys_hint = (
                    f"[SYSTEM CONTEXT — INTERNAL, DO NOT REPEAT TO CUSTOMER]: "
                    f"Order ID / Email detected: {info_str}. "
                    f"This is ONLY an identifier. You have NO order data yet. "
                    f"Your ONLY valid next output is: Action: query_order(order_id=\"{known_info[0]}\")"
                )
            else:
                # Order already queried successfully — guide toward resolution
                sys_hint = (
                    f"[SYSTEM CONTEXT — INTERNAL]: Order {info_str} has already been verified. "
                    f"The order data is in your conversation history. "
                    f"Do NOT call query_order again. "
                    f"Focus on resolving the customer's request using the data you already have, "
                    f"or clearly explain why it cannot be fulfilled and offer the best alternative."
                )
            agent_input = f"{customer_msg}\n\n{sys_hint}"
            
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

            # --- [NEW] Farewell Priority Check ---
            # If the agent responds with a farewell/polite closing, we skip strict format checks
            is_closing = is_farewell(service_final) or any(kw in service_final.lower() for kw in ["welcome", "assist you"])
            
            # ReAct Mode Observation Injection (Closed-Loop with improved parsing)
            react_iter = 0
            react_no_action_count = 0  # Counter for consecutive responses without Action/Final Answer
            while not is_closing and agent_type == "ReAct" and "Action:" in service_final and react_iter < 5:
                react_iter += 1
                if "Observation:" in service_final:
                    service_final = service_final.split("Observation:")[0].strip()
                
                # IMPROVED REGEX: Support both format:
                # - Action: query_order(ORD556)
                # - Action: query_order(order_id="ORD556")
                # - Action: query_order(email="user@example.com")
                match = re.search(r"Action:\s*(\w+)\s*\((.*?)\)", service_final, re.DOTALL)
                if match:
                    tool_name = match.group(1)
                    tool_args_raw = match.group(2).strip()
                    
                    # Enhanced parameter extraction
                    tool_param = None
                    if "=" in tool_args_raw:
                        # Format: order_id="ORD556" or email="user@example.com"
                        param_key, param_value = tool_args_raw.split("=", 1)
                        tool_param = param_value.strip().strip('"').strip("'")
                    else:
                        # Format: ORD556 (direct value)
                        tool_param = tool_args_raw.strip().strip('"').strip("'")
                    
                    # Validation: forbid certain patterns
                    if not tool_param or tool_param.lower() in ["none", "null", "undefined", ""]:
                        print(f"!!! [RE-ACT VALIDATION FAILED] Invalid parameter: {tool_param}. Terminating ReAct loop.")
                        break
                    
                    print(f"--- [RE-ACT INTERCEPT] Executing: {tool_name}({tool_param}) (Iter {react_iter}) ---")
                    
                    if hasattr(service_agent, "_execute_tool"):
                        observation = service_agent._execute_tool(tool_name, tool_param, case_id)
                    else:
                        from src.tools.simulator import ToolSimulator
                        sim = ToolSimulator()
                        if tool_name == "query_order": 
                            observation = sim.query_order(case_id, tool_param)
                        elif tool_name == "track_shipping": 
                            observation = sim.track_shipping(case_id, tool_param)
                        elif tool_name == "apply_refund":
                            order_id, reason = self._parse_order_action_args(tool_args_raw)
                            if order_id:
                                observation = sim.apply_refund(case_id, order_id, reason)
                            else:
                                observation = "Error: apply_refund requires a valid order_id (ORDxxx format)."
                        elif tool_name == "cancel_order":
                            order_id, reason = self._parse_order_action_args(tool_args_raw)
                            if order_id:
                                observation = sim.cancel_order(case_id, order_id, reason)
                            else:
                                observation = "Error: cancel_order requires a valid order_id (ORDxxx format)."
                        else:
                            observation = f"Error: Tool '{tool_name}' not found. Only query_order, track_shipping, apply_refund, cancel_order are allowed."
                    
                    print(f"--- [RE-ACT OBSERVATION]: {observation} ---")
                    if isinstance(observation, dict) and observation.get("status") == "success":
                        if tool_name == "query_order":
                            query_verified = True
                        elif tool_name in ("apply_refund", "cancel_order"):
                            task_resolved = True
                            tool_triggered = True
                            final_resolution = "EXECUTED_SUCCESSFULLY"
                    obs_prompt = f"Observation: {observation}"
                    service_final, next_usage = service_agent.run(obs_prompt, case_id=case_id)
                    for k in service_usage: service_usage[k] += next_usage[k]
                    react_no_action_count = 0  # Reset counter on successful action
                    # Re-check closing after observation
                    is_closing = is_farewell(service_final) or any(kw in service_final.lower() for kw in ["welcome", "assist you"])
                else:
                    # No valid Action found in this iteration
                    react_no_action_count += 1
                    print(f"!!! [RE-ACT] No valid Action found. Count: {react_no_action_count}/2")
                    
                    # DEADLOCK PREVENTION: If 2 consecutive iterations without Action/Final Answer, force terminate
                    if react_no_action_count >= 2 or (react_iter >= 3 and "Final Answer:" not in service_final):
                        print("!!! [RE-ACT DEADLOCK] Detected loop without action/answer. Force terminating ReAct loop.")
                        # Try to extract any meaningful content as final response
                        if service_final.strip():
                            pass  # Use current service_final
                        else:
                            service_final = "Thank you for contacting us. How can I assist you further?"
                        break
                    break
            
            if react_iter >= 5:
                print("!!! [RUNNER] ReAct max iterations reached. Breaking tool loop.")

            # --- Single-slot Mode Tool Injection (with improved parsing) ---
            if agent_type == "Single-slot" and "Action:" in service_final:
                match = re.search(r"Action:\s*(\w+)\s*\((.*?)\)", service_final, re.DOTALL)
                if match:
                    tool_name = match.group(1)
                    tool_args_raw = match.group(2).strip()
                    
                    # Enhanced parameter extraction (same as ReAct)
                    tool_param = None
                    if "=" in tool_args_raw:
                        param_key, param_value = tool_args_raw.split("=", 1)
                        tool_param = param_value.strip().strip('"').strip("'")
                    else:
                        tool_param = tool_args_raw.strip().strip('"').strip("'")
                    
                    print(f"--- [SINGLE-SLOT INTERCEPT] Executing: {tool_name}({tool_param}) ---")
                    
                    from src.tools.simulator import ToolSimulator
                    sim = ToolSimulator()
                    if tool_name == "query_order":
                        observation = sim.query_order(case_id, tool_param)
                    elif tool_name == "track_shipping":
                        observation = sim.track_shipping(case_id, tool_param)
                    elif tool_name == "apply_refund":
                        order_id, reason = self._parse_order_action_args(tool_args_raw)
                        if order_id:
                            observation = sim.apply_refund(case_id, order_id, reason)
                        else:
                            observation = "Error: apply_refund requires a valid order_id (ORDxxx format)."
                    elif tool_name == "cancel_order":
                        order_id, reason = self._parse_order_action_args(tool_args_raw)
                        if order_id:
                            observation = sim.cancel_order(case_id, order_id, reason)
                        else:
                            observation = "Error: cancel_order requires a valid order_id (ORDxxx format)."
                    else:
                        observation = f"Error: Tool '{tool_name}' not found. Only query_order, track_shipping, apply_refund, cancel_order are allowed."
                    
                    print(f"--- [SINGLE-SLOT OBSERVATION]: {observation} ---")

                    # Track actual tool execution — no keyword guessing needed
                    tool_triggered = True
                    if isinstance(observation, dict) and observation.get("status") == "success":
                        if tool_name == "query_order":
                            query_verified = True
                        elif tool_name in ("apply_refund", "cancel_order"):
                            task_resolved = True
                            final_resolution = "EXECUTED_SUCCESSFULLY"

                    obs_prompt = f"Observation: {observation}"
                    service_final, next_usage = service_agent.run(obs_prompt, case_id=case_id)
                    for k in service_usage: service_usage[k] += next_usage[k]

            # --- [NEW] Strict Format & Meta-talk Validation ---
            forbidden_meta_patterns = [
                r"\(Note:.*\)", r"\(I am waiting.*\)", r"waiting for tool", r"I will now call",
                r"I'm sorry, as an AI",
                # Instruction leakage: agent narrating its own decision logic
                r"(?:Since|Because) the .{0,60}(?:is not|are not|isn't|aren't).{0,60}(?:dialogue|history|conversation)",
                r"I will (?:ask them for|proceed to ask|now ask)",
                r"(?:Based on |)OPTION [ABC]",
                r"Option [ABC]\s*[—\-→🗙✓✗]",
                r"(?:Since|Because) (?:no |the customer).{0,40}(?:Order ID|Email).{0,40}(?:present|provided|found|given)",
                r"\[YOUR DECISION\]",
                r"OPTION [ABC] —",
            ]
            if any(re.search(pattern, service_final, re.IGNORECASE) for pattern in forbidden_meta_patterns):
                print(f"!!! [RUNNER] Meta-talk detected in agent response. Triggering retry...")
                retry_prompt = "[SYSTEM]: Your response contained forbidden meta-talk or parenthetical notes. Please provide your response again using ONLY Thought and Action/Final Answer tags. DO NOT explain your actions."
                service_final, next_usage = service_agent.run(retry_prompt, case_id=case_id)
                for k in service_usage: service_usage[k] += next_usage[k]

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
                print(">>> [TERMINATION] Loop detected in agent responses.")
                status = "LOOP_FAILURE"
                break
            response_history.append(service_final)

            # --- Task Completion Check ---
            full_trace = service_agent.history[-1]["content"]
            
            # [REFINED] Precise Success/Refusal Detection
            if "Observation:" in full_trace:
                # Check for critical tool success
                is_execution_success = any(cmd in full_trace for cmd in ["apply_refund", "cancel_order"]) and \
                                      any(ok in full_trace for ok in ["'status': 'success'", '"status": "success"'])
                
                if is_execution_success:
                    task_resolved = True
                    tool_triggered = True
                    final_resolution = "EXECUTED_SUCCESSFULLY"
                
                # Check for query success or status verification
                elif "query_order" in full_trace and any(ok in full_trace for ok in ["'status': 'success'", '"status": "success"']):
                    tool_triggered = True
                    # If verified and refusal keywords present
                    refusal_keywords = ["cannot", "unable", "policy", "unfortunately", "no longer eligible", "outside the return window"]
                    if any(k in service_final.lower() for k in refusal_keywords):
                        task_resolved = True
                        final_resolution = "RESOLVED_WITH_REFUSAL"
                    elif any(k in service_final.lower() for k in ["shipped", "delivered", "status is"]):
                        task_resolved = True # Informational task resolved
                        final_resolution = "INFO_PROVIDED"

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
                 print(">>> [TERMINATION] Signal detected: Agent signaled end of conversation.")
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
        
        # Ensure directories exist and add debug prints
        log_dir = "outputs/logs"
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"log_{case_id}_{agent_type}_{persona_type}.json")
        
        print(f"Debug: Starting save to {log_path}...")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=4, ensure_ascii=False)
            print("Debug: Save complete")
        except Exception as e:
            print(f"Debug: Save failed with error: {e}")
            
        print(f">>> Finished with Status: {status}. Saved to {log_path}\n")
        return log_data

if __name__ == "__main__":
    with open("data/fact_sheets.json", "r", encoding="utf-8") as f:
        all_facts = json.load(f)
    runner = DialogueRunner()
    runner.run_conversation("CASE_141", all_facts["CASE_141"], "Single-slot", "Polite")
