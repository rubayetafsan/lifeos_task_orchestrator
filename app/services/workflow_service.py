from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Workflow, WorkflowStatus, Task, TaskStatus
from app.schemas.task import WorkflowCreate, WorkflowUpdate, PaginationMeta, TaskCreate
from app.core.logging import get_logger
from app.services.task_service import TaskService

logger = get_logger(__name__)


class WorkflowService:
    """Service for workflow orchestration."""
    
    @staticmethod
    async def create_workflow(
        db: AsyncSession,
        workflow_data: WorkflowCreate
    ) -> Workflow:
        """Create a new workflow with tasks."""
        workflow = Workflow(
            name=workflow_data.name,
            description=workflow_data.description,
            config=workflow_data.config,
            input_data=workflow_data.input_data,
            status=WorkflowStatus.DRAFT
        )
        
        db.add(workflow)
        await db.flush()
        
        # Create associated tasks
        if workflow_data.tasks:
            for task_data in workflow_data.tasks:
                task_create = TaskCreate(**task_data.model_dump())
                task_create.workflow_id = workflow.id
                await TaskService.create_task(db, task_create)
        
        await db.refresh(workflow)
        logger.info(f"Created workflow: {workflow.id} - {workflow.name}")
        return workflow
    
    @staticmethod
    async def get_workflow(
        db: AsyncSession,
        workflow_id: UUID,
        include_tasks: bool = True
    ) -> Optional[Workflow]:
        """Get workflow by ID."""
        query = select(Workflow).where(Workflow.id == workflow_id)
        
        if include_tasks:
            query = query.options(selectinload(Workflow.tasks))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_workflows(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[WorkflowStatus] = None
    ) -> Tuple[List[Workflow], PaginationMeta]:
        """List workflows with filtering and pagination."""
        query = select(Workflow)
        
        if status:
            query = query.where(Workflow.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = (
            query
            .options(selectinload(Workflow.tasks))
            .order_by(Workflow.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        workflows = list(result.scalars().all())
        
        meta = PaginationMeta(
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            page_size=limit,
            total_pages=(total + limit - 1) // limit if limit > 0 else 1
        )
        
        return workflows, meta
    
    @staticmethod
    async def update_workflow(
        db: AsyncSession,
        workflow_id: UUID,
        workflow_update: WorkflowUpdate
    ) -> Optional[Workflow]:
        """Update workflow."""
        workflow = await WorkflowService.get_workflow(db, workflow_id, include_tasks=False)
        if not workflow:
            return None
        
        update_data = workflow_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workflow, field, value)
        
        workflow.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(workflow)
        
        logger.info(f"Updated workflow: {workflow.id}")
        return workflow
    
    @staticmethod
    async def delete_workflow(
        db: AsyncSession,
        workflow_id: UUID
    ) -> bool:
        """Delete workflow and associated tasks."""
        workflow = await WorkflowService.get_workflow(db, workflow_id, include_tasks=False)
        if not workflow:
            return False
        
        await db.delete(workflow)
        await db.flush()
        
        logger.info(f"Deleted workflow: {workflow_id}")
        return True
    
    @staticmethod
    async def execute_workflow(
        db: AsyncSession,
        workflow_id: UUID,
        input_data: Optional[dict] = None
    ) -> Workflow:
        """Execute all tasks in a workflow."""
        workflow = await WorkflowService.get_workflow(db, workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Update workflow status
        workflow.status = WorkflowStatus.ACTIVE
        workflow.started_at = datetime.utcnow()
        if input_data:
            workflow.input_data = input_data
        await db.flush()
        
        logger.info(f"Executing workflow {workflow.id} with {len(workflow.tasks)} tasks")
        
        try:
            # Get execution order
            tasks = await WorkflowService._get_execution_order(workflow)
            
            # Execute tasks in order
            results = []
            for task in tasks:
                # Merge workflow input with task input
                task_input = {**(workflow.input_data or {}), **(task.input_data or {})}
                
                # Execute task
                executed_task = await TaskService.execute_task(db, task.id, task_input)
                results.append(executed_task)
                
                # If task failed and workflow should stop on failure
                if executed_task.status == TaskStatus.FAILED:
                    stop_on_failure = workflow.config.get("stop_on_failure", True) if workflow.config else True
                    if stop_on_failure:
                        logger.warning(f"Workflow {workflow.id} stopped due to task failure")
                        workflow.status = WorkflowStatus.FAILED
                        break
            
            # Check overall workflow status
            if workflow.status != WorkflowStatus.FAILED:
                all_completed = all(t.status == TaskStatus.COMPLETED for t in results)
                workflow.status = WorkflowStatus.COMPLETED if all_completed else WorkflowStatus.FAILED
            
            workflow.completed_at = datetime.utcnow()
            
            # Aggregate output data
            workflow.output_data = {
                "tasks_executed": len(results),
                "tasks_completed": sum(1 for t in results if t.status == TaskStatus.COMPLETED),
                "tasks_failed": sum(1 for t in results if t.status == TaskStatus.FAILED),
                "task_results": [
                    {
                        "task_id": str(t.id),
                        "task_name": t.name,
                        "status": t.status.value,
                        "output": t.output_data
                    }
                    for t in results
                ]
            }
            
            logger.info(f"Workflow {workflow.id} execution completed with status {workflow.status}")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.utcnow()
            logger.error(f"Workflow {workflow.id} execution failed: {str(e)}")
            raise
        
        await db.flush()
        await db.refresh(workflow)
        return workflow
    
    @staticmethod
    async def _get_execution_order(workflow: Workflow) -> List[Task]:
        """
        Determine task execution order based on dependencies.
        
        For now, uses simple sequential order. In production, this would
        parse the workflow config for DAG-based dependencies.
        """
        # Sort tasks by creation order (or priority)
        return sorted(workflow.tasks, key=lambda t: (t.priority.value, t.created_at))
    
    @staticmethod
    async def pause_workflow(
        db: AsyncSession,
        workflow_id: UUID
    ) -> Optional[Workflow]:
        """Pause workflow execution."""
        workflow = await WorkflowService.get_workflow(db, workflow_id, include_tasks=False)
        if not workflow:
            return None
        
        workflow.status = WorkflowStatus.PAUSED
        workflow.updated_at = datetime.utcnow()
        await db.flush()
        
        logger.info(f"Paused workflow: {workflow.id}")
        return workflow
    
    @staticmethod
    async def resume_workflow(
        db: AsyncSession,
        workflow_id: UUID
    ) -> Optional[Workflow]:
        """Resume paused workflow."""
        workflow = await WorkflowService.get_workflow(db, workflow_id, include_tasks=False)
        if not workflow or workflow.status != WorkflowStatus.PAUSED:
            return None
        
        workflow.status = WorkflowStatus.ACTIVE
        workflow.updated_at = datetime.utcnow()
        await db.flush()
        
        logger.info(f"Resumed workflow: {workflow.id}")
        return workflow
