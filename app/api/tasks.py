from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskExecute,
    TaskListResponse,
    TaskStatusResponse,
    TaskExecutionResponse
)
from app.models.task import TaskStatus, TaskPriority
from app.services.task_service import TaskService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task"
)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Create a new task.
    
    - **name**: Task name (required)
    - **task_type**: Type of task (email, data_processing, notification)
    - **priority**: Task priority (low, medium, high, critical)
    - **input_data**: Task-specific input parameters
    - **scheduled_at**: Optional scheduled execution time
    """
    created_task = await TaskService.create_task(db, task)
    return TaskResponse.model_validate(created_task)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List all tasks"
)
async def list_tasks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    workflow_id: Optional[UUID] = Query(None, description="Filter by workflow ID"),
    db: AsyncSession = Depends(get_db)
) -> TaskListResponse:
    """
    List tasks with optional filtering and pagination.
    
    Supports filtering by status, priority, and workflow ID.
    """
    tasks, meta = await TaskService.list_tasks(
        db,
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        workflow_id=workflow_id
    )
    
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        meta=meta
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task by ID"
)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Get detailed information about a specific task."""
    task = await TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task"
)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Update task properties."""
    task = await TaskService.update_task(db, task_id, task_update)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task"
)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a task."""
    deleted = await TaskService.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )


@router.post(
    "/{task_id}/execute",
    response_model=TaskResponse,
    summary="Execute task immediately"
)
async def execute_task(
    task_id: UUID,
    execute_data: Optional[TaskExecute] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Execute a task immediately.
    
    Can optionally provide input data that overrides the task's configured input.
    """
    input_data = execute_data.input_data if execute_data else None
    
    try:
        task = await TaskService.execute_task(db, task_id, input_data)
        return TaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {str(e)}"
        )


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="Get task status"
)
async def get_task_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> TaskStatusResponse:
    """Get quick status of a task."""
    task = await TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    # Calculate progress if task is running
    progress = None
    if task.status == TaskStatus.RUNNING:
        # In a real implementation, this would track actual progress
        progress = 50.0
    elif task.status == TaskStatus.COMPLETED:
        progress = 100.0
    
    return TaskStatusResponse(
        id=task.id,
        status=task.status,
        progress=progress,
        message=task.error_message if task.error_message else None
    )


@router.get(
    "/{task_id}/executions",
    response_model=List[TaskExecutionResponse],
    summary="Get task execution history"
)
async def get_task_executions(
    task_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> List[TaskExecutionResponse]:
    """Get execution history for a task."""
    # Verify task exists
    task = await TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    executions = await TaskService.get_task_executions(db, task_id)
    return [TaskExecutionResponse.model_validate(e) for e in executions]
