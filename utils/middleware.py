"""
Custom middleware for request tracking and logging
"""

import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logging_utils import get_logger, set_request_id, clear_request_id, log_request_start, log_request_complete

logger = get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and logging"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Set request ID in context
        set_request_id(request_id)
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request start
        start_time = time.time()
        log_request_start(
            logger=logger,
            endpoint=str(request.url.path),
            method=request.method,
            request_id=request_id,
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request completion
            log_request_complete(
                logger=logger,
                endpoint=str(request.url.path),
                method=request.method,
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            from utils.logging_utils import log_error
            log_error(
                logger=logger,
                error_type="request_error",
                message=f"Request failed: {str(e)}",
                request_id=request_id,
                exception=e
            )
            
            # Re-raise the exception
            raise
            
        finally:
            # Clear request ID from context
            clear_request_id()
