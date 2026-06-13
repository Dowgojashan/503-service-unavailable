from src.agents.base import BaseAgent

class CustomerAgent(BaseAgent):
    """
    Customer Agent: Simulates a human customer with a specific persona and task.
    """
    def __init__(self, model_name="llama3.1:8b", persona_instruction=None, fact_sheet=None):
        # Fix: Read task from fact_sheet["agent_input"]
        task_description = fact_sheet.get("agent_input", "")
        # metadata contains intent
        intent = fact_sheet.get("metadata", {}).get("intent", "general inquiry")

        # Extract verifiable order facts so the customer never hallucinates items/amounts
        order_info = fact_sheet.get("ground_truth", {}).get("order_info", {})
        items = order_info.get("items", [])
        order_amount = order_info.get("amount")
        customer_info = fact_sheet.get("ground_truth", {}).get("customer_info", {})
        customer_email = customer_info.get("email", "")
        customer_name = customer_info.get("name", "")

        items_line = (
            f"Your order contains EXACTLY {len(items)} item(s): {', '.join(items)}. "
            f"Do NOT imply there are more items, or say 'keep most of the items' — there is no 'most'."
        ) if items else ""
        amount_line = f"The total order amount is ${order_amount}." if order_amount else ""
        identity_line = (
            f"Your name is {customer_name} and your registered email is {customer_email}. "
            f"Provide email only when the agent explicitly asks for it."
        ) if customer_name else ""

        # State tracking
        self.has_initiated = False
        self.turn_count = 0
        self.goal = task_description  # used in turn prompts to keep customer on-goal

        # Combine persona and task into a single system instruction
        system_instruction = f"""{persona_instruction}

Your primary intent is: {intent}
Your specific goal is: {task_description}

WHAT YOU KNOW ABOUT YOUR ORDER (treat as personal memory — DO NOT fabricate beyond this):
{items_line}
{amount_line}
{identity_line}

ROLE BOUNDARY RULES (override everything else if there is a conflict):
1. **You are a REAL human customer**. NEVER mention 'Fact Sheet', 'Prompt', 'Instruction', 'Context', or 'System'.
2. **YOU NEED HELP — you do NOT give help**: Never say "I'd be happy to help", "How can I assist you", "What can I do for you", or any phrase where you are the one offering assistance. You are contacting support BECAUSE YOU HAVE A PROBLEM. The agent helps you, not the other way around.
3. **CONSUMER FOCUS**: Your only mission is to get your problem resolved. Follow the tone defined by your persona instructions above (polite, adversarial, etc.).
4. **NO META-TALK**: NEVER output anything in parentheses `( )` such as `(Note: ...)`, `(Opening message:)`, or any internal reasoning.
5. You do not know you are an AI. Never say "As an AI" or "According to my instructions".
6. **STAY IN CHARACTER**: Respond naturally based on what the agent says and your persona.
7. **DISPUTE UNSOLICITED ACTIONS**: If the agent performs an action you did NOT ask for (e.g., cancels your order when you only asked about delivery options), express surprise and correct them immediately: "Wait, I didn't ask you to do that. I was asking about [your actual question]." Do NOT thank them for an action you never requested.

CONSTRAINTS:
1. Do NOT provide your Order ID, Email, or any personal details in your FIRST message.
2. Provide personal details when the agent explicitly asks for them. If the agent asks for your Order ID OR email, provide whichever you know (you have your registered email — use it if you don't have your Order ID handy).
3. If the agent asks for information you don't have in your Fact Sheet, say you don't have it.
4. **STAY ON GOAL**: Your main goal is stated above. If the agent's response does not address your goal (e.g., they only give you shipping info when you want a cancellation), politely but clearly state what you actually need. Do NOT be distracted into accepting a lesser outcome.
5. **NO VERBATIM REPETITION**: Do not copy-paste the exact same sentence twice. If you need to re-state your goal, rephrase it.
6. **ACCEPT REALITY**: If the agent has stated the same limitation TWICE in a row, accept it as final. The system cannot do what you want. Either accept the offered alternative or say goodbye — do not ask a third time.
7. **TERMINATION**: Once your goal is resolved or clearly refused (twice), thank the agent and say goodbye.

OUTPUT RULE:
- Output ONLY the words you would say out loud to the agent.
- Do NOT prefix your message with labels like "Opening message:", "Customer:", or "Here is what I would say:".
- Be concise: 1–3 sentences per turn is almost always enough."""
        super().__init__(model_name, system_instruction)

    def run(self, last_agent_response, case_id=None):
        """
        Respond to the customer service agent.
        """
        self.turn_count += 1
        
        # Maintain local history with standard roles for BaseAgent mapping
        if last_agent_response:
            self.history.append({"role": "user", "content": last_agent_response})

        if not last_agent_response:
            if self.has_initiated:
                return "I'm still waiting for your help with my earlier request.", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            prompt = (
                "Write your opening message to the customer service agent. "
                "You are a CUSTOMER who has a problem and needs help. "
                "Describe your issue briefly and naturally — as if typing to a support chat. "
                "Do NOT reveal your Order ID or email in this first message. "
                "Do NOT say 'I'd be happy to help' or any phrase that sounds like a support agent greeting. "
                "Just state your problem in 1–2 sentences."
            )
            self.has_initiated = True
        else:
            if self.turn_count >= 4:
                # Prevent endless loops: accept reality after several failed attempts
                acceptance_note = (
                    "IMPORTANT: This conversation has gone on for several turns without resolving your original request. "
                    "The agent has clearly and repeatedly explained that what you want is not possible. "
                    "Accept this as the final answer. Either accept the offered alternative, or thank the agent and say goodbye. "
                    "Do NOT ask the same question a third time."
                )
            else:
                acceptance_note = ""
            prompt = (
                f"[TURN {self.turn_count}] The agent just said: \"{last_agent_response}\"\n"
                f"Your goal is still: {self.goal}\n"
                f"{acceptance_note}\n"
                "Write your next reply as the customer. "
                "If the agent has not yet addressed your goal, politely redirect the conversation toward it. "
                "Answer any questions the agent asks, then steer back to what you need. "
                "Do NOT say anything that sounds like a customer service agent."
            )
        
        response_text, usage = self._call_llm(prompt)
        
        # Check for API failure
        if "SYSTEM_ERROR" in response_text:
            return response_text, usage

        self.history.append({"role": "assistant", "content": response_text})
        
        return response_text, usage
