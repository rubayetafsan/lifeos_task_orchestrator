from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskStatus, TaskPriority, TaskExecution
from app.schemas.task import TaskCreate, TaskUpdate, PaginationMeta
from app.core.logging import get_logger
from app.agents.registry import agent_registry

logger = get_logger(__name__)


class TaskService:
    """Service for task operations."""
    
    @staticmethod
    async def create_task(
        db: AsyncSession,
        task_data: TaskCreate
    ) -> Task:
        """Create a new task."""
        task = Task(
            name=task_data.name,
            description=task_data.description,
            task_type=task_data.task_type,
            priority=task_data.priority,
            input_data=task_data.input_data,
            scheduled_at=task_data.scheduled_at,
            webhook_url=task_data.webhook_url,
            max_retries=task_data.max_retries,
            workflow_id=task_data.workflow_id,
            status=TaskStatus.PENDING
        )
        
        db.add(task)
        await db.flush()
        await db.refresh(task)
        
        logger.info(f"Created task: {task.id} - {task.name}")
        return task
    
    @staticmethod
    async def get_task(
        db: AsyncSession,
        task_id: UUID
    ) -> Optional[Task]:
        """Get task by ID."""
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        workflow_id: Optional[UUID] = None
    ) -> Tuple[List[Task], PaginationMeta]:
        """List tasks with filtering and pagination."""
        # Build query
        query = select(Task)
        
        # Apply filters
        filters = []
        if status:
            filters.append(Task.status == status)
        if priority:
            filters.append(Task.priority == priority)
        if workflow_id:
            filters.append(Task.workflow_id == workflow_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        tasks = list(result.scalars().all())
        
        # Build pagination metadata
        meta = PaginationMeta(
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            page_size=limit,
            total_pages=(total + limit - 1) // limit if limit > 0 else 1
        )
        
        return tasks, meta
    
    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: UUID,
        task_update: TaskUpdate
    ) -> Optional[Task]:
        """Update task."""
        task = await TaskService.get_task(db, task_id)
        if not task:
            return None
        
        # Update fields
        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        task.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(task)
        
        logger.info(f"Updated task: {task.id}")
        return task
    
    @staticmethod
    async def delete_task(
        db: AsyncSession,
        task_id: UUID
    ) -> bool:
        """Delete task."""
        task = await TaskService.get_task(db, task_id)
        if not task:
            return False
        
        await db.delete(task)
        await db.flush()
        
        logger.info(f"Deleted task: {task_id}")
        return True
    
    @staticmethod
    async def execute_task(
        db: AsyncSession,
        task_id: UUID,
        input_data: Optional[dict] = None
    ) -> Task:
        """Execute a task using the appropriate agent."""
        task = await TaskService.get_task(db, task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        if input_data:
            task.input_data = input_data
        await db.flush()
        
        # Create execution log
        execution = TaskExecution(
            task_id=task.id,
            status=TaskStatus.RUNNING,
            attempt_number=task.retry_count + 1,
            started_at=datetime.utcnow()
        )
        db.add(execution)
        await db.flush()
        
        try:
            # Get appropriate agent
            agent = agent_registry.get_agent(task.task_type)
            
            # Execute task
            logger.info(f"Executing task {task.id} with agent {agent.agent_type}")
            result = await agent.execute(task.id, task.input_data or {})
            
            # Update task with success
            task.status = TaskStatus.COMPLETED
            task.output_data = result
            task.completed_at = datetime.utcnow()
            
            # Update execution log
            execution.status = TaskStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.execution_data = result
            
            logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            # Update task with failure
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.retry_count += 1
            
            # Update execution log
            execution.status = TaskStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(e)
            
            logger.error(f"Task {task.id} failed: {str(e)}")
            
            # Check if should retry
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                logger.info(f"Task {task.id} will retry ({task.retry_count}/{task.max_retries})")
        
        await db.flush()
        await db.refresh(task)
        return task
    
    @staticmethod
    async def get_task_executions(
        db: AsyncSession,
        task_id: UUID
    ) -> List[TaskExecution]:
        """Get execution history for a task."""
        result = await db.execute(
            select(TaskExecution)
            .where(TaskExecution.task_id == task_id)
            .order_by(TaskExecution.created_at.desc())
        )
        return list(result.scalars().all())
