from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.schemas.task import HealthCheckResponse
from app.core.config import settings
from app.agents.registry import agent_registry

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint"
)
async def health_check(
    db: AsyncSession = Depends(get_db)
) -> HealthCheckResponse:
    """
    Check the health status of the service.
    
    Returns:
    - Service status
    - Version information
    - Database connectivity
    - Other subsystem status
    """
    # Check database connection
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
    
    return HealthCheckResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.APP_VERSION,
        database=db_status
    )


@router.get(
    "/agents",
    summary="List available agents"
)
async def list_agents():
    """
    List all registered task agents and their capabilities.
    
    Shows which task types are supported by the system.
    """
    agents = agent_registry.list_agents()
    
    # Add descriptions for each agent type
    agent_info = {
        "email": {
            "type": "email",
            "description": "Handles email operations",
            "actions": ["send", "categorize", "filter", "reply", "forward"]
        },
        "data_processing": {
            "type": "data_processing",
            "description": "Processes and transforms data",
            "operations": ["transform", "validate", "aggregate", "analyze", "export"]
        },
        "notification": {
            "type": "notification",
            "description": "Sends notifications across channels",
            "channels": ["email", "sms", "push", "webhook", "slack", "teams"]
        }
    }
    
    return {
        "registered_agents": agents,
        "agent_details": agent_info,
        "total_agents": len(agents)
    }
