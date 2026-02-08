from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.task import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowExecute,
    WorkflowListResponse
)
from app.models.task import WorkflowStatus
from app.services.workflow_service import WorkflowService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workflow"
)
async def create_workflow(
    workflow: WorkflowCreate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """
    Create a new workflow with associated tasks.
    
    - **name**: Workflow name (required)
    - **description**: Workflow description
    - **config**: Workflow configuration (dependencies, execution order)
    - **tasks**: List of tasks to include in the workflow
    """
    created_workflow = await WorkflowService.create_workflow(db, workflow)
    return WorkflowResponse.model_validate(created_workflow)


@router.get(
    "",
    response_model=WorkflowListResponse,
    summary="List all workflows"
)
async def list_workflows(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[WorkflowStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowListResponse:
    """
    List workflows with optional filtering and pagination.
    
    Supports filtering by status.
    """
    workflows, meta = await WorkflowService.list_workflows(
        db,
        skip=skip,
        limit=limit,
        status=status
    )
    
    return WorkflowListResponse(
        items=[WorkflowResponse.model_validate(w) for w in workflows],
        meta=meta
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Get workflow by ID"
)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Get detailed information about a specific workflow including all tasks."""
    workflow = await WorkflowService.get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    return WorkflowResponse.model_validate(workflow)


@router.patch(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Update workflow"
)
async def update_workflow(
    workflow_id: UUID,
    workflow_update: WorkflowUpdate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Update workflow properties."""
    workflow = await WorkflowService.update_workflow(db, workflow_id, workflow_update)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    return WorkflowResponse.model_validate(workflow)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workflow"
)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a workflow and all associated tasks."""
    deleted = await WorkflowService.delete_workflow(db, workflow_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )


@router.post(
    "/{workflow_id}/execute",
    response_model=WorkflowResponse,
    summary="Execute workflow"
)
async def execute_workflow(
    workflow_id: UUID,
    execute_data: Optional[WorkflowExecute] = None,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """
    Execute a workflow, running all tasks in order.
    
    Can optionally provide input data that will be merged with each task's input.
    """
    input_data = execute_data.input_data if execute_data else None
    
    try:
        workflow = await WorkflowService.execute_workflow(db, workflow_id, input_data)
        return WorkflowResponse.model_validate(workflow)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


@router.post(
    "/{workflow_id}/pause",
    response_model=WorkflowResponse,
    summary="Pause workflow execution"
)
async def pause_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Pause a running workflow."""
    workflow = await WorkflowService.pause_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    return WorkflowResponse.model_validate(workflow)


@router.post(
    "/{workflow_id}/resume",
    response_model=WorkflowResponse,
    summary="Resume paused workflow"
)
async def resume_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Resume a paused workflow."""
    workflow = await WorkflowService.resume_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found or not paused"
        )
    return WorkflowResponse.model_validate(workflow)
