from typing import Dict, Type
from app.agents.base import BaseAgent
from app.agents.email_agent import EmailAgent
from app.agents.data_agent import DataProcessingAgent
from app.agents.notification_agent import NotificationAgent


class AgentRegistry:
    """
    Registry for managing and accessing task agents.
    
    Provides a centralized way to register and retrieve agents
    based on task type.
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._register_default_agents()
    
    def _register_default_agents(self) -> None:
        """Register default built-in agents."""
        self.register("email", EmailAgent())
        self.register("data_processing", DataProcessingAgent())
        self.register("notification", NotificationAgent())
    
    def register(self, task_type: str, agent: BaseAgent) -> None:
        """
        Register an agent for a specific task type.
        
        Args:
            task_type: Type of tasks this agent handles
            agent: Agent instance
        """
        self._agents[task_type] = agent
    
    def get_agent(self, task_type: str) -> BaseAgent:
        """
        Get agent for a specific task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If no agent found for task type
        """
        agent = self._agents.get(task_type)
        if not agent:
            raise ValueError(
                f"No agent registered for task type: {task_type}. "
                f"Available types: {list(self._agents.keys())}"
            )
        return agent
    
    def list_agents(self) -> Dict[str, str]:
        """
        List all registered agents.
        
        Returns:
            Dict mapping task types to agent types
        """
        return {
            task_type: agent.agent_type 
            for task_type, agent in self._agents.items()
        }
    
    def is_registered(self, task_type: str) -> bool:
        """Check if agent is registered for task type."""
        return task_type in self._agents


# Global agent registry instance
agent_registry = AgentRegistry()
