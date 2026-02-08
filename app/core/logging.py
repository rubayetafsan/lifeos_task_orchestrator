import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from contextvars import ContextVar

from app.core.config import settings

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get('')
        return True


class CustomJsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'environment': settings.ENVIRONMENT
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id') and record.correlation_id:
            log_data['correlation_id'] = record.correlation_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure application logging."""
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.JSON_LOGS:
        # JSON formatter for production
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(console_handler)
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with correlation ID support."""
    logger = logging.getLogger(name)
    logger.addFilter(CorrelationIdFilter())
    return logger


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """Get correlation ID from current context."""
    return correlation_id_var.get('')
