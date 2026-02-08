from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.models.task import TaskStatus, TaskPriority, WorkflowStatus


# ============================================================================
# Task Schemas
# ============================================================================

class TaskBase(BaseModel):
    """Base task schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: str = Field(..., description="Type of task (e.g., email, data_processing, notification)")
    priority: TaskPriority = TaskPriority.MEDIUM
    input_data: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    webhook_url: Optional[str] = Field(None, max_length=500)
    max_retries: int = Field(3, ge=0, le=10)


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    workflow_id: Optional[UUID] = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    input_data: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    webhook_url: Optional[str] = None


class TaskResponse(TaskBase):
    """Schema for task response."""
    id: UUID
    status: TaskStatus
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    workflow_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)


class TaskExecute(BaseModel):
    """Schema for executing a task immediately."""
    input_data: Optional[Dict[str, Any]] = None


# ============================================================================
# Workflow Schemas
# ============================================================================

class WorkflowBase(BaseModel):
    """Base workflow schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Workflow configuration (e.g., task dependencies, execution order)"
    )
    input_data: Optional[Dict[str, Any]] = None


class WorkflowCreate(WorkflowBase):
    """Schema for creating a workflow."""
    tasks: Optional[List[TaskCreate]] = Field(
        None,
        description="Tasks to include in workflow"
    )


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    config: Optional[Dict[str, Any]] = None
    input_data: Optional[Dict[str, Any]] = None


class WorkflowResponse(WorkflowBase):
    """Schema for workflow response."""
    id: UUID
    status: WorkflowStatus
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tasks: List[TaskResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowExecute(BaseModel):
    """Schema for executing a workflow."""
    input_data: Optional[Dict[str, Any]] = None


# ============================================================================
# Execution Log Schemas
# ============================================================================

class TaskExecutionResponse(BaseModel):
    """Schema for task execution log response."""
    id: UUID
    task_id: UUID
    status: TaskStatus
    attempt_number: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# List Response Schemas
# ============================================================================

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskListResponse(BaseModel):
    """Schema for paginated task list."""
    items: List[TaskResponse]
    meta: PaginationMeta


class WorkflowListResponse(BaseModel):
    """Schema for paginated workflow list."""
    items: List[WorkflowResponse]
    meta: PaginationMeta


# ============================================================================
# Status Response
# ============================================================================

class TaskStatusResponse(BaseModel):
    """Quick task status response."""
    id: UUID
    status: TaskStatus
    progress: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=100.0,
        description="Task progress percentage"
    )
    message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: str = "connected"
    pubsub: Optional[str] = None
