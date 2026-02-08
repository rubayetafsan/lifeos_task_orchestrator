import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.core.config import settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/lifeos_test"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestAsyncSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient):
    """Test task creation."""
    task_data = {
        "name": "Test Email Task",
        "description": "Send a test email",
        "task_type": "email",
        "priority": "medium",
        "input_data": {
            "action": "send",
            "to": "test@example.com",
            "subject": "Test",
            "body": "Test email"
        }
    }
    
    response = await client.post("/api/v1/tasks", json=task_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == task_data["name"]
    assert data["task_type"] == task_data["task_type"]
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient):
    """Test listing tasks."""
    # Create a task first
    task_data = {
        "name": "Test Task",
        "task_type": "notification",
        "input_data": {"channel": "email", "message": "Test"}
    }
    await client.post("/api/v1/tasks", json=task_data)
    
    # List tasks
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "meta" in data
    assert len(data["items"]) > 0


@pytest.mark.asyncio
async def test_create_workflow(client: AsyncClient):
    """Test workflow creation."""
    workflow_data = {
        "name": "Test Workflow",
        "description": "A test workflow",
        "tasks": [
            {
                "name": "Task 1",
                "task_type": "email",
                "input_data": {"action": "send", "to": "test@example.com"}
            },
            {
                "name": "Task 2",
                "task_type": "notification",
                "input_data": {"channel": "slack", "message": "Workflow complete"}
            }
        ]
    }
    
    response = await client.post("/api/v1/workflows", json=workflow_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == workflow_data["name"]
    assert len(data["tasks"]) == 2
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    """Test listing available agents."""
    response = await client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert "registered_agents" in data
    assert "email" in data["registered_agents"]
    assert "data_processing" in data["registered_agents"]
    assert "notification" in data["registered_agents"]
