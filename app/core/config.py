from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "LifeOS Task Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lifeos"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Google Cloud Platform
    GCP_PROJECT_ID: Optional[str] = None
    GCP_REGION: str = "us-central1"
    PUBSUB_TASK_TOPIC: str = "task-events"
    PUBSUB_WORKFLOW_TOPIC: str = "workflow-events"
    
    # Redis (for background tasks)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Task Processing
    MAX_RETRY_ATTEMPTS: int = 3
    TASK_TIMEOUT_SECONDS: int = 300
    WORKER_CONCURRENCY: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
