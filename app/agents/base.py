from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Base agent interface for task execution.
    
    All agents must implement the execute method and handle their specific
    task type processing logic.
    """
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.logger = get_logger(f"{__name__}.{agent_type}")
    
    @abstractmethod
    async def execute(
        self, 
        task_id: uuid.UUID,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the task with given input data.
        
        Args:
            task_id: Unique task identifier
            input_data: Task input parameters
            
        Returns:
            Dict containing execution results
            
        Raises:
            Exception: If execution fails
        """
        pass
    
    @abstractmethod
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data before execution.
        
        Args:
            input_data: Task input parameters
            
        Returns:
            True if valid, raises exception otherwise
        """
        pass
    
    async def pre_execute(self, task_id: uuid.UUID, input_data: Dict[str, Any]) -> None:
        """Hook called before task execution."""
        self.logger.info(
            f"Starting task execution",
            extra={
                "task_id": str(task_id),
                "agent_type": self.agent_type
            }
        )
    
    async def post_execute(
        self, 
        task_id: uuid.UUID, 
        result: Dict[str, Any],
        success: bool
    ) -> None:
        """Hook called after task execution."""
        self.logger.info(
            f"Task execution {'succeeded' if success else 'failed'}",
            extra={
                "task_id": str(task_id),
                "agent_type": self.agent_type,
                "success": success
            }
        )
    
    async def handle_error(
        self, 
        task_id: uuid.UUID, 
        error: Exception
    ) -> Dict[str, Any]:
        """
        Handle execution errors.
        
        Args:
            task_id: Task identifier
            error: Exception that occurred
            
        Returns:
            Error information dict
        """
        self.logger.error(
            f"Task execution failed: {str(error)}",
            extra={
                "task_id": str(task_id),
                "agent_type": self.agent_type,
                "error": str(error)
            },
            exc_info=True
        )
        
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }


class AgentExecutionResult:
    """Wrapper for agent execution results."""
    
    def __init__(
        self,
        success: bool,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.output_data = output_data or {}
        self.error_message = error_message
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
