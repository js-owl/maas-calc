"""
API versioning utilities
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from constants import APP_VERSION


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for API versioning"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add version headers
        response.headers["X-API-Version"] = APP_VERSION
        response.headers["X-API-Name"] = "Manufacturing Calculation API"
        
        return response


def get_api_version() -> str:
    """Get current API version"""
    return APP_VERSION


def get_version_info() -> dict:
    """Get comprehensive version information"""
    return {
        "api_version": APP_VERSION,
        "api_name": "Manufacturing Calculation API",
        "api_type": "REST",
        "api_format": "JSON",
        "supported_versions": ["3.1.0"],
        "deprecated_versions": [],
        "versioning_strategy": "header-based"
    }
