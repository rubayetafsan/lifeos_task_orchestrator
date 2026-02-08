from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum as PyEnum
import uuid

from sqlalchemy import String, Integer, DateTime, JSON, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class TaskStatus(str, PyEnum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(str, PyEnum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowStatus(str, PyEnum):
    """Workflow execution status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    """Task model for individual task execution."""
    
    __tablename__ = "tasks"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Core Fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Status & Priority
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), 
        default=TaskStatus.PENDING, 
        nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), 
        default=TaskPriority.MEDIUM, 
        nullable=False
    )
    
    # Execution Data
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Retry Logic
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=True
    )
    workflow: Mapped[Optional["Workflow"]] = relationship(
        "Workflow", 
        back_populates="tasks"
    )
    
    # Webhook
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Task {self.id} - {self.name} ({self.status})>"


class Workflow(Base):
    """Workflow model for orchestrating multiple tasks."""
    
    __tablename__ = "workflows"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Core Fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), 
        default=WorkflowStatus.DRAFT, 
        nullable=False
    )
    
    # Configuration
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Execution Data
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    tasks: Mapped[list["Task"]] = relationship(
        "Task", 
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Workflow {self.id} - {self.name} ({self.status})>"


class TaskExecution(Base):
    """Task execution log for audit trail."""
    
    __tablename__ = "task_executions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False
    )
    
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<TaskExecution {self.id} - Task {self.task_id} Attempt {self.attempt_number}>"
