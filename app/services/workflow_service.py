from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models.task import Workflow, Task, WorkflowStatus, TaskStatus
from app.schemas.task import WorkflowCreate, WorkflowUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowService:
    
    @staticmethod
    async def create_workflow(
        db: AsyncSession,
        workflow_data: WorkflowCreate
    ) -> Workflow:
        workflow = Workflow(
            name=workflow_data.name,
            description=workflow_data.description,
            config=workflow_data.config or {},
            input_data=workflow_data.input_data,
            status=WorkflowStatus.DRAFT
        )
        db.add(workflow)
        await db.flush()
        
        for task_data in workflow_data.tasks:
            task = Task(
                workflow_id=workflow.id,
                name=task_data.name,
                task_type=task_data.task_type,
                priority=task_data.priority,
                input_data=task_data.input_data or {},
                status=TaskStatus.PENDING
            )
            db.add(task)
        
        await db.commit()
        
        stmt = (
            select(Workflow)
            .where(Workflow.id == workflow.id)
            .options(selectinload(Workflow.tasks))
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one()
        
        logger.info(f"Created workflow {workflow.id} with {len(workflow.tasks)} tasks")
        return workflow
    
    @staticmethod
    async def get_workflow(
        db: AsyncSession,
        workflow_id: UUID
    ) -> Optional[Workflow]:
        stmt = (
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.tasks))
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()
        
        if workflow:
            logger.debug(f"Retrieved workflow {workflow_id} with {len(workflow.tasks)} tasks")
        
        return workflow
    
    @staticmethod
    async def list_workflows(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[WorkflowStatus] = None
    ) -> Tuple[List[Workflow], Dict[str, Any]]:
        stmt = select(Workflow).options(selectinload(Workflow.tasks))
        
        if status:
            stmt = stmt.where(Workflow.status == status)
        
        count_stmt = select(func.count()).select_from(Workflow)
        if status:
            count_stmt = count_stmt.where(Workflow.status == status)
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        stmt = stmt.offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        workflows = result.scalars().all()
        
        page = (skip // limit) + 1 if limit > 0 else 1
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        
        meta = {
            "total": total,
            "page": page,
            "page_size": limit,
            "total_pages": total_pages
        }
        
        logger.debug(f"Listed {len(workflows)} workflows (total: {total})")
        return list(workflows), meta
    
    @staticmethod
    async def update_workflow(
        db: AsyncSession,
        workflow_id: UUID,
        workflow_update: WorkflowUpdate
    ) -> Optional[Workflow]:
        workflow = await WorkflowService.get_workflow(db, workflow_id)
        if not workflow:
            return None
        
        update_data = workflow_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workflow, field, value)
        
        workflow.updated_at = datetime.utcnow()
        
        await db.commit()
        
        stmt = (
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.tasks))
        )
        result = await db.execute(stmt)
        workflow = result.scalar_one()
        
        logger.info(f"Updated workflow {workflow_id}")
        return workflow
    
    @staticmethod
    async def delete_workflow(
        db: AsyncSession,
        workflow_id: UUID
    ) -> bool:
        workflow = await WorkflowService.get_workflow(db, workflow_id)
        if not workflow:
            return False
        
        await db.delete(workflow)
        await db.commit()
        
        logger.info(f"Deleted workflow {workflow_id}")
        return True
    
    @staticmethod
    async def execute_workflow(
        db: AsyncSession,
        workflow_id: UUID,
        input_data: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        workflow = await WorkflowService.get_workflow(db, workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if workflow.status == WorkflowStatus.ACTIVE:
            raise ValueError(f"Workflow is already running")
        
        workflow.status = WorkflowStatus.ACTIVE
        workflow.started_at = datetime.utcnow()
        
        if input_data:
            workflow.input_data = {**(workflow.input_data or {}), **input_data}
        
        await db.commit()
        
        try:
            for task in workflow.tasks:
                logger.info(f"Executing task {task.id} ({task.name})")
                
                task.status = TaskStatus.RUNNING
                if hasattr(task, 'started_at'):
                    task.started_at = datetime.utcnow()
                await db.commit()
                
                task_input = {**(workflow.input_data or {}), **(task.input_data or {})}
                
                try:
                    result = await WorkflowService._execute_task(task, task_input)
                    
                    task.status = TaskStatus.COMPLETED
                    task.output_data = result
                    if hasattr(task, 'completed_at'):
                        task.completed_at = datetime.utcnow()
                    
                except Exception as task_error:
                    logger.error(f"Task {task.id} failed: {str(task_error)}")
                    task.status = TaskStatus.FAILED
                    if hasattr(task, 'error_message'):
                        task.error_message = str(task_error)
                    task.output_data = {"error": str(task_error)}
                    
                    workflow.status = WorkflowStatus.FAILED
                    workflow.completed_at = datetime.utcnow()
                    await db.commit()
                    
                    return await WorkflowService.get_workflow(db, workflow_id)
                
                await db.commit()
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.utcnow()
            await db.commit()
            raise ValueError(f"Workflow execution failed: {str(e)}")
        
        return await WorkflowService.get_workflow(db, workflow_id)
    
    @staticmethod
    async def _execute_task(
        task: Task,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if task.task_type == "email":
            return {
                "status": "sent",
                "recipient": input_data.get("to"),
                "subject": input_data.get("subject"),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif task.task_type == "data_processing":
            return {
                "status": "processed",
                "operation": input_data.get("operation"),
                "records_processed": len(input_data.get("data", [])),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif task.task_type == "notification":
            return {
                "status": "delivered",
                "channel": input_data.get("channel"),
                "message": input_data.get("message"),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif task.task_type == "http_request":
            return {
                "status": "success",
                "url": input_data.get("url"),
                "method": input_data.get("method", "GET"),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            return {
                "status": "completed",
                "task_type": task.task_type,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    async def pause_workflow(
        db: AsyncSession,
        workflow_id: UUID
    ) -> Optional[Workflow]:
        workflow = await WorkflowService.get_workflow(db, workflow_id)
        if not workflow:
            return None
        
        if workflow.status != WorkflowStatus.ACTIVE:
            logger.warning(f"Cannot pause workflow {workflow_id} - not running")
            return None
        
        workflow.status = WorkflowStatus.PAUSED
        await db.commit()
        
        logger.info(f"Paused workflow {workflow_id}")
        
        return await WorkflowService.get_workflow(db, workflow_id)
    
    @staticmethod
    async def resume_workflow(
        db: AsyncSession,
        workflow_id: UUID
    ) -> Optional[Workflow]:
        workflow = await WorkflowService.get_workflow(db, workflow_id)
        if not workflow:
            return None
        
        if workflow.status != WorkflowStatus.PAUSED:
            logger.warning(f"Cannot resume workflow {workflow_id} - not paused")
            return None
        
        workflow.status = WorkflowStatus.ACTIVE
        await db.commit()
        
        logger.info(f"Resumed workflow {workflow_id}")
        
        return await WorkflowService.get_workflow(db, workflow_id)