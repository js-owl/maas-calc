"""
Standardized logging utilities
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar

# Context variable for request ID
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add request ID if available
        request_id = request_id_context.get()
        if request_id:
            log_entry["request_id"] = request_id
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class LoggerManager:
    """Centralized logger management"""
    
    def __init__(self):
        self._loggers = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Setup root logger with structured formatting"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler with structured formatter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get logger with standardized configuration"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_request_id(self, request_id: str):
        """Set request ID for current context"""
        request_id_context.set(request_id)
    
    def clear_request_id(self):
        """Clear request ID from current context"""
        request_id_context.set(None)


# Global logger manager instance
logger_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    """Get standardized logger"""
    return logger_manager.get_logger(name)


def set_request_id(request_id: str):
    """Set request ID for logging context"""
    logger_manager.set_request_id(request_id)


def clear_request_id():
    """Clear request ID from logging context"""
    logger_manager.clear_request_id()


def log_request_start(
    logger: logging.Logger,
    endpoint: str,
    method: str,
    request_id: str,
    file_id: Optional[str] = None,
    service_id: Optional[str] = None,
    **kwargs
):
    """Log request start with standardized format"""
    extra_fields = {
        "event_type": "request_start",
        "endpoint": endpoint,
        "method": method,
        "file_id": file_id,
        "service_id": service_id,
        **kwargs
    }
    
    logger.info(
        f"Request started: {method} {endpoint}",
        extra={"extra_fields": extra_fields}
    )


def log_request_complete(
    logger: logging.Logger,
    endpoint: str,
    method: str,
    request_id: str,
    status_code: int,
    duration_ms: float,
    file_id: Optional[str] = None,
    service_id: Optional[str] = None,
    **kwargs
):
    """Log request completion with standardized format"""
    extra_fields = {
        "event_type": "request_complete",
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "file_id": file_id,
        "service_id": service_id,
        **kwargs
    }
    
    logger.info(
        f"Request completed: {method} {endpoint} - {status_code} ({duration_ms}ms)",
        extra={"extra_fields": extra_fields}
    )


def log_calculation_start(
    logger: logging.Logger,
    service_type: str,
    file_id: str,
    request_id: str,
    **kwargs
):
    """Log calculation start with standardized format"""
    extra_fields = {
        "event_type": "calculation_start",
        "service_type": service_type,
        "file_id": file_id,
        **kwargs
    }
    
    logger.info(
        f"Starting {service_type} calculation for file_id: {file_id}",
        extra={"extra_fields": extra_fields}
    )


def log_calculation_complete(
    logger: logging.Logger,
    service_type: str,
    file_id: str,
    request_id: str,
    duration_ms: float,
    **kwargs
):
    """Log calculation completion with standardized format"""
    extra_fields = {
        "event_type": "calculation_complete",
        "service_type": service_type,
        "file_id": file_id,
        "duration_ms": duration_ms,
        **kwargs
    }
    
    logger.info(
        f"Completed {service_type} calculation for file_id: {file_id} ({duration_ms}ms)",
        extra={"extra_fields": extra_fields}
    )


def log_error(
    logger: logging.Logger,
    error_type: str,
    message: str,
    file_id: Optional[str] = None,
    request_id: Optional[str] = None,
    exception: Optional[Exception] = None,
    **kwargs
):
    """Log error with standardized format"""
    extra_fields = {
        "event_type": "error",
        "error_type": error_type,
        "file_id": file_id,
        **kwargs
    }
    
    logger.error(
        f"{error_type}: {message}",
        extra={"extra_fields": extra_fields},
        exc_info=exception
    )


def log_warning(
    logger: logging.Logger,
    warning_type: str,
    message: str,
    file_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs
):
    """Log warning with standardized format"""
    extra_fields = {
        "event_type": "warning",
        "warning_type": warning_type,
        "file_id": file_id,
        **kwargs
    }
    
    logger.warning(
        f"{warning_type}: {message}",
        extra={"extra_fields": extra_fields}
    )
