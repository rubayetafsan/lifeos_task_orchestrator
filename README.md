# LifeOS Task Orchestrator

FastAPI-based task and workflow execution service built with cloud-native architecture for Google Cloud Platform.

![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## Overview

LifeOS Task Orchestrator is a scalable, cloud-ready service that enables multi step workflow execution through a modular agent based architecture. It demonstrates production grade patterns for building microservices on GCP.

### Key Features

- ✅ **Agent-Based Architecture**: Modular, extensible task processors
- ✅ **Async Processing**: Non-blocking execution with FastAPI
- ✅ **Workflow Orchestration**: Chain tasks with dependencies
- ✅ **Priority Queuing**: Execute critical tasks first
- ✅ **Retry Logic**: Automatic retry with configurable limits
- ✅ **Status Tracking**: Real-time monitoring of task progress
- ✅ **Cloud-Native**: Designed for GCP (Cloud Run, Cloud SQL, Pub/Sub)
- ✅ **Production Ready**: Logging, monitoring, health checks, error handling

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Tasks   │  │Workflows │  │  System  │  │  Health  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
┌───────▼─────────────▼─────────────▼─────────────▼──────────┐
│                      Service Layer                          │
│  ┌────────────────┐           ┌──────────────────┐         │
│  │  Task Service  │           │ Workflow Service │         │
│  └───────┬────────┘           └────────┬─────────┘         │
└──────────┼─────────────────────────────┼───────────────────┘
           │                             │
┌──────────▼─────────────────────────────▼───────────────────┐
│                      Agent Layer                            │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Email  │  │     Data     │  │Notification  │          │
│  │  Agent  │  │  Processing  │  │    Agent     │          │
│  └─────────┘  │    Agent     │  └──────────────┘          │
│               └──────────────┘                             │
└────────────────────────────────────────────────────────────┘
           │                             │
┌──────────▼─────────────────────────────▼───────────────────┐
│                   Persistence Layer                         │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐              │
│  │ PostgreSQL  │  │  Redis   │  │ Pub/Sub  │              │
│  └─────────────┘  └──────────┘  └──────────┘              │
└────────────────────────────────────────────────────────────┘
```

### Components

#### 1. **API Layer** (`app/api/`)
- RESTful endpoints for tasks, workflows, and system operations
- OpenAPI/Swagger documentation
- Request validation with Pydantic

#### 2. **Service Layer** (`app/services/`)
- Business logic separation
- Transaction management
- Workflow orchestration logic

#### 3. **Agent Layer** (`app/agents/`)
- Modular task processors
- Pluggable architecture
- Three built-in agents:
  - **Email Agent**: Send, categorize, filter emails
  - **Data Processing Agent**: Transform, validate, aggregate data
  - **Notification Agent**: Multi-channel notifications

#### 4. **Models & Schemas** (`app/models/`, `app/schemas/`)
- SQLAlchemy ORM models
- Pydantic schemas for validation
- Type-safe data structures

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+ (or use Docker)
- Google Cloud SDK (for GCP deployment)

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/lifeos-task-orchestrator.git
cd lifeos-task-orchestrator
```

2. **Set up environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run with Docker Compose**
```bash
docker-compose up -d
```

4. **Access the API**
- API Documentation: http://localhost:8080/docs
- Alternative Docs: http://localhost:8080/redoc
- Health Check: http://localhost:8080/api/v1/health

### Manual Setup (Without Docker)

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up PostgreSQL**
```bash
createdb lifeos
```

4. **Run the application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## 📚 API Usage Examples

### Creating a Task

```bash
curl -X POST "http://localhost:8080/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Send Welcome Email",
    "task_type": "email",
    "priority": "high",
    "input_data": {
      "action": "send",
      "to": "user@example.com",
      "subject": "Welcome!",
      "body": "Thanks for joining!"
    }
  }'
```

### Executing a Task

```bash
curl -X POST "http://localhost:8080/api/v1/tasks/{task_id}/execute"
```

### Creating a Workflow

```bash
curl -X POST "http://localhost:8080/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Onboarding",
    "description": "Complete onboarding workflow",
    "tasks": [
      {
        "name": "Send Welcome Email",
        "task_type": "email",
        "priority": "high",
        "input_data": {
          "action": "send",
          "to": "user@example.com",
          "subject": "Welcome!"
        }
      },
      {
        "name": "Create User Profile",
        "task_type": "data_processing",
        "input_data": {
          "operation": "transform",
          "data": []
        }
      },
      {
        "name": "Notify Team",
        "task_type": "notification",
        "input_data": {
          "channel": "slack",
          "message": "New user registered!"
        }
      }
    ]
  }'
```

### Executing a Workflow

```bash
curl -X POST "http://localhost:8080/api/v1/workflows/{workflow_id}/execute"
```

## ☁️ GCP Deployment

### Prerequisites

1. Google Cloud account with billing enabled
2. gcloud CLI installed and configured
3. Docker installed

### Deployment Steps

1. **Set your GCP project**
```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
```

2. **Run deployment script**
```bash
chmod +x deployment/deploy-gcp.sh
./deployment/deploy-gcp.sh
```

This script will:
- Enable required GCP APIs
- Build and push Docker image to GCR
- Create Cloud SQL PostgreSQL instance
- Set up Pub/Sub topics
- Deploy to Cloud Run

### Manual Deployment

```bash
# Build and push image
docker build -t gcr.io/${GCP_PROJECT_ID}/lifeos-task-orchestrator:latest .
docker push gcr.io/${GCP_PROJECT_ID}/lifeos-task-orchestrator:latest

# Deploy to Cloud Run
gcloud run deploy lifeos-task-orchestrator \
  --image gcr.io/${GCP_PROJECT_ID}/lifeos-task-orchestrator:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 10
```

### Environment Variables for Production

Set these in Cloud Run or Secret Manager:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Application secret key (min 32 chars)
- `GCP_PROJECT_ID`: Your GCP project ID
- `ENVIRONMENT`: Set to "production"
- `JSON_LOGS`: Set to "true"

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api.py::test_create_task
```

## Monitoring & Observability

### Structured Logging

All logs include:
- Correlation IDs for request tracking
- Structured JSON format in production
- Log levels: DEBUG, INFO, WARNING, ERROR

### Health Checks

```bash
curl http://localhost:8080/api/v1/health
```

Returns:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-07T16:30:00Z",
  "database": "connected"
}
```

### Metrics (GCP)

When deployed to Cloud Run, automatic metrics include:
- Request count
- Request latency
- Error rate
- Container CPU/memory usage

## 🔧 Configuration

### Environment Variables

See `.env.example` for all configuration options.

Key configurations:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `GCP_PROJECT_ID` | GCP project ID | - |
| `SECRET_KEY` | Application secret | - |
| `LOG_LEVEL` | Logging level | INFO |
| `MAX_RETRY_ATTEMPTS` | Max task retry count | 3 |

## Development

### Adding a New Agent

1. Create agent file in `app/agents/`:

```python
from app.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("my_agent")
    
    async def validate_input(self, input_data):
        # Validation logic
        return True
    
    async def execute(self, task_id, input_data):
        # Execution logic
        return {"result": "success"}
```

2. Register in `app/agents/registry.py`:

```python
from app.agents.my_agent import MyAgent

def _register_default_agents(self):
    # ... existing agents
    self.register("my_agent", MyAgent())
```

### Code Style

```bash
# Format code
black app/ tests/

# Lint code
ruff app/ tests/
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request


## Acknowledgments

- FastAPI framework
- SQLAlchemy ORM
- Google Cloud Platform

---
