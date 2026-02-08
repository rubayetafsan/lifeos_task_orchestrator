# Architecture Documentation

## System Overview

LifeOS Task Orchestrator is built using a layered architecture pattern with clear separation of concerns. This document details the architectural decisions and design patterns used.

## Architecture Layers

### 1. API Layer (FastAPI)

**Location**: `app/api/`

**Responsibilities**:
- HTTP request handling
- Request/response validation
- OpenAPI documentation generation
- Error handling and status codes
- CORS configuration

**Key Components**:
- `tasks.py`: Task CRUD and execution endpoints
- `workflows.py`: Workflow orchestration endpoints
- `system.py`: Health checks and system info

**Design Patterns**:
- Dependency Injection (FastAPI's Depends)
- Router pattern for endpoint organization
- Middleware chain for cross-cutting concerns

### 2. Service Layer

**Location**: `app/services/`

**Responsibilities**:
- Business logic implementation
- Transaction management
- Data transformation
- Orchestration logic

**Key Components**:
- `TaskService`: Task operations (CRUD, execution)
- `WorkflowService`: Workflow orchestration

**Design Patterns**:
- Service pattern
- Repository pattern (via SQLAlchemy)
- Unit of Work (database transactions)

### 3. Agent Layer

**Location**: `app/agents/`

**Responsibilities**:
- Task execution logic
- Type-specific processing
- Error handling
- Input validation

**Key Components**:
- `BaseAgent`: Abstract base class
- `EmailAgent`: Email operations
- `DataProcessingAgent`: Data transformations
- `NotificationAgent`: Multi-channel notifications
- `AgentRegistry`: Agent management

**Design Patterns**:
- Strategy pattern (different agents for different tasks)
- Registry pattern (agent lookup)
- Template method (BaseAgent)
- Dependency injection

### 4. Data Layer

**Location**: `app/models/`, `app/db/`

**Responsibilities**:
- Data persistence
- Schema definitions
- Database migrations
- Connection management

**Key Components**:
- SQLAlchemy models (Task, Workflow, TaskExecution)
- Async database session management
- Connection pooling

**Design Patterns**:
- Active Record (SQLAlchemy ORM)
- Repository pattern
- Connection pooling

## Data Flow

### Task Execution Flow

```
1. HTTP Request → API Layer
   POST /api/v1/tasks/{id}/execute
   
2. API Layer → Service Layer
   TaskService.execute_task()
   
3. Service Layer → Agent Registry
   Get appropriate agent for task_type
   
4. Agent Registry → Specific Agent
   EmailAgent.execute()
   
5. Agent → External Services
   Send email, process data, etc.
   
6. Agent → Service Layer
   Return execution result
   
7. Service Layer → Database
   Update task status and output
   
8. Service Layer → API Layer
   Return task response
   
9. API Layer → Client
   HTTP 200 with task details
```

### Workflow Execution Flow

```
1. Client → API: POST /workflows/{id}/execute
2. WorkflowService: Load workflow + tasks
3. For each task in execution order:
   a. TaskService: Execute task
   b. Agent: Process task
   c. Update task status
4. Aggregate results
5. Update workflow status
6. Return workflow response
```

## Database Schema

### Core Tables

#### tasks
```sql
- id (UUID, PK)
- name (VARCHAR)
- description (TEXT)
- task_type (VARCHAR)
- status (ENUM: pending, running, completed, failed, etc.)
- priority (ENUM: low, medium, high, critical)
- input_data (JSONB)
- output_data (JSONB)
- error_message (TEXT)
- retry_count (INT)
- max_retries (INT)
- workflow_id (UUID, FK to workflows)
- scheduled_at (TIMESTAMP)
- started_at (TIMESTAMP)
- completed_at (TIMESTAMP)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

#### workflows
```sql
- id (UUID, PK)
- name (VARCHAR)
- description (TEXT)
- status (ENUM: draft, active, paused, completed, failed)
- config (JSONB)
- input_data (JSONB)
- output_data (JSONB)
- started_at (TIMESTAMP)
- completed_at (TIMESTAMP)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

#### task_executions
```sql
- id (UUID, PK)
- task_id (UUID, FK)
- status (ENUM)
- attempt_number (INT)
- started_at (TIMESTAMP)
- completed_at (TIMESTAMP)
- error_message (TEXT)
- execution_data (JSONB)
- created_at (TIMESTAMP)
```

### Relationships

- Workflow → Tasks (One-to-Many)
- Task → TaskExecutions (One-to-Many)

## Async Processing

### Why Async?

1. **I/O Bound Operations**: Most task operations involve I/O (database, external APIs)
2. **Concurrent Execution**: Handle multiple requests simultaneously
3. **Resource Efficiency**: Better resource utilization than threading
4. **Scalability**: Higher throughput with same resources

### Implementation

```python
# Async database sessions
async with AsyncSessionLocal() as session:
    result = await session.execute(query)

# Async agent execution
async def execute(self, task_id, input_data):
    await self.pre_execute(task_id, input_data)
    result = await self._perform_operation()
    return result
```

## Error Handling Strategy

### Levels of Error Handling

1. **Agent Level**
   - Validate input
   - Handle execution errors
   - Return error information

2. **Service Level**
   - Update task status
   - Implement retry logic
   - Log failures

3. **API Level**
   - Convert to HTTP status codes
   - Format error responses
   - Log request context

### Retry Logic

```python
if task.retry_count < task.max_retries:
    task.status = TaskStatus.RETRYING
    task.retry_count += 1
else:
    task.status = TaskStatus.FAILED
```

## Logging & Observability

### Structured Logging

All logs include:
- Correlation ID (request tracking)
- Timestamp
- Log level
- Environment
- Contextual data

### Log Levels

- **DEBUG**: Development details
- **INFO**: Normal operations
- **WARNING**: Unexpected but handled situations
- **ERROR**: Failures requiring attention

### Correlation IDs

Every request gets a unique correlation ID:
```python
correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
```

This enables tracking a request through all layers.

## Security Considerations

### Authentication (Not Implemented)

For production, add:
- JWT tokens
- API keys
- OAuth2 integration

### Input Validation

- Pydantic schemas validate all inputs
- Type checking at API boundary
- SQL injection prevention (SQLAlchemy ORM)

### Secrets Management

- Environment variables for config
- GCP Secret Manager for production
- Never commit secrets to git

## Scalability

### Horizontal Scaling

The application is stateless and can scale horizontally:
- Cloud Run auto-scaling (1-10 instances)
- Load balancing included
- Shared database state

### Performance Optimizations

1. **Database**
   - Connection pooling
   - Async queries
   - Indexed columns (id, status, created_at)

2. **Application**
   - Async processing
   - Minimal middleware overhead
   - Lazy loading of relationships

3. **Caching** (Future)
   - Redis for task queue
   - Cache frequently accessed data

## Cloud-Native Design

### GCP Services Used

1. **Cloud Run**: Serverless container hosting
2. **Cloud SQL**: Managed PostgreSQL
3. **Pub/Sub**: Event messaging
4. **Secret Manager**: Configuration management
5. **Cloud Logging**: Centralized logs
6. **Container Registry**: Docker images

### Benefits

- **Auto-scaling**: Based on traffic
- **Pay-per-use**: Cost-efficient
- **Managed services**: Less operational overhead
- **High availability**: Built-in redundancy

## Future Enhancements

### Short Term

1. **Background Task Queue**: Celery + Redis
2. **Webhook Callbacks**: Notify on completion
3. **Rate Limiting**: Prevent abuse
4. **API Authentication**: JWT tokens

### Long Term

1. **DAG-based Workflows**: Complex dependencies
2. **Scheduled Tasks**: Cron-like execution
3. **Workflow Templates**: Reusable patterns
4. **Real-time Updates**: WebSocket support
5. **Metrics Dashboard**: Grafana integration
6. **Multi-tenancy**: Organization support

## Design Decisions

### Why FastAPI?

- Modern, fast Python framework
- Native async support
- Automatic OpenAPI documentation
- Type hints and validation
- Production-ready features

### Why SQLAlchemy?

- Mature ORM with async support
- Database-agnostic
- Migration support (Alembic)
- Type-safe queries

### Why Agent Pattern?

- Separation of concerns
- Easy to add new task types
- Testable in isolation
- Clear responsibility boundaries

### Why PostgreSQL?

- JSONB support for flexible data
- ACID compliance
- GCP managed service available
- Excellent performance

## Testing Strategy

### Unit Tests

- Agent logic
- Service methods
- Utility functions

### Integration Tests

- API endpoints
- Database operations
- Workflow execution

### Test Coverage

- Minimum 50% coverage
- Critical paths: 80%+ coverage

## Deployment Architecture

### Development

```
Docker Compose
├── PostgreSQL container
├── Redis container
└── API container (with hot reload)
```

### Production (Cloud Run)

```
Cloud Run Service
├── Auto-scaling instances (1-10)
├── Load balancer
└── Connections to:
    ├── Cloud SQL (PostgreSQL)
    ├── Pub/Sub topics
    └── Secret Manager
```

## Monitoring & Alerts

### Metrics to Monitor

1. **Application**
   - Request rate
   - Response time
   - Error rate
   - Task success rate

2. **Infrastructure**
   - CPU usage
   - Memory usage
   - Database connections
   - Query performance

3. **Business**
   - Tasks created per hour
   - Average execution time
   - Retry rate
   - Workflow completion rate

### Alerting Thresholds

- Error rate > 5%
- Response time > 2s (p95)
- Database connection pool > 80%
- Failed tasks > 10/min

---

**Last Updated**: February 2026
**Version**: 1.0.0
