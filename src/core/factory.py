from src.agents.single_slot import SingleSlotAgent
from src.agents.react_agent import ReActAgent
from src.agents.reflection_agent import ReflectionAgent
from src.agents.plan_execute_agent import PlanExecuteAgent

class AgentFactory:
    @staticmethod
    def create_agent(agent_type, model_name="gemini-1.5-flash", system_instruction=None):
        """
        Factory method to create an agent based on the specified type.
        """
        if agent_type == "Single-slot":
            return SingleSlotAgent(model_name, system_instruction)
        elif agent_type == "ReAct":
            return ReActAgent(model_name, system_instruction)
        elif agent_type == "Reflection":
            return ReflectionAgent(model_name, system_instruction)
        elif agent_type == "PlanExecute":
            return PlanExecuteAgent(model_name, system_instruction)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
