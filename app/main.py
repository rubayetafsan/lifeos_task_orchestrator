import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import setup_logging, get_logger, set_correlation_id
from app.db.session import init_db, close_db
from app.api import tasks, workflows, system

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    LifeOS Task Orchestrator
    
    A production ready task and workflow execution service built with FastAPI and cloud native architecture.
    
    Features

    1. Multi-step Workflow Engine - Chain tasks with dependencies
    2. gent-based Architecture - Modular processors for different task types
    3. Async Processing - Non-blocking execution with background tasks
    4. Status Tracking* - Real-time monitoring of task and workflow progress
    5. Retry Logic - Automatic retry with exponential backoff
    6. Priority Queue - Execute critical tasks first
    
    Supported Task Types

    1. Email - Send, categorize, filter, reply, forward
    2. Data Processing - Transform, validate, aggregate, analyze, export
    3. Notification - Multi-channel notifications (email, SMS, push, webhook, Slack, Teams)
    
    Getting Started

    1. Create a task using `POST /api/v1/tasks`
    2. Execute it with `POST /api/v1/tasks/{id}/execute`
    3. Monitor status with `GET /api/v1/tasks/{id}/status`
    
    For complex workflows, create a workflow with `POST /api/v1/workflows` and execute with
    `POST /api/v1/workflows/{id}/execute`.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# Correlation ID Middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID to all requests."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    set_correlation_id(correlation_id)
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Request Logging Middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests."""
    logger.info(
        f"Request started",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None
        }
    )
    
    response = await call_next(request)
    
    logger.info(
        f"Request completed",
        extra={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code
        }
    )
    
    return response


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(
        f"Validation error",
        extra={
            "url": str(request.url),
            "errors": exc.errors()
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        f"Unhandled exception",
        extra={
            "url": str(request.url),
            "error": str(exc)
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# Include routers
app.include_router(system.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)
app.include_router(workflows.router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
