"""
Standardized response utilities
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import Request
from models.error_models import (
    StandardErrorResponse, ValidationErrorResponse, 
    FileProcessingErrorResponse, CalculationErrorResponse,
    ServiceUnavailableErrorResponse, NotFoundErrorResponse,
    ErrorDetail
)
from constants import ERROR_MESSAGES, ERROR_CODES, HTTP_STATUS_CODES, APP_VERSION


class ResponseWrapper:
    """Standardized response wrapper for consistent API responses"""
    
    @staticmethod
    def success_response(
        data: Any,
        message: str = "Request completed successfully",
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized success response"""
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "version": APP_VERSION
        }
        
        if request_id:
            response["request_id"] = request_id
            
        if metadata:
            response["metadata"] = metadata
            
        return response
    
    @staticmethod
    def error_response(
        error_type: str,
        error_message: str,
        error_code: str,
        details: Optional[List[ErrorDetail]] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create standardized error response"""
        
        # Map error types to response classes
        error_classes = {
            "validation": ValidationErrorResponse,
            "file_processing": FileProcessingErrorResponse,
            "calculation": CalculationErrorResponse,
            "service_unavailable": ServiceUnavailableErrorResponse,
            "not_found": NotFoundErrorResponse
        }
        
        error_class = error_classes.get(error_type, StandardErrorResponse)
        
        response_data = {
            "error": error_message,
            "error_code": error_code,
            "details": details,
            "request_id": request_id,
            "path": path,
            "method": method
        }
        
        response = error_class(**response_data).model_dump()
        
        # Add status code to response metadata
        status_code = HTTP_STATUS_CODES.get(error_code, 500)
        response["status_code"] = status_code
        
        return response
    
    @staticmethod
    def validation_error(
        field: str,
        message: str,
        value: Any = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create validation error response"""
        detail = ErrorDetail(field=field, message=message, value=value)
        
        return ResponseWrapper.error_response(
            error_type="validation",
            error_message=ERROR_MESSAGES["validation_error"],
            error_code=ERROR_CODES["VALIDATION_ERROR"],
            details=[detail],
            request_id=request_id,
            path=path,
            method=method
        )
    
    @staticmethod
    def file_processing_error(
        message: str,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create file processing error response"""
        return ResponseWrapper.error_response(
            error_type="file_processing",
            error_message=message,
            error_code=ERROR_CODES["FILE_PROCESSING_ERROR"],
            request_id=request_id,
            path=path,
            method=method
        )
    
    @staticmethod
    def calculation_error(
        message: str,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create calculation error response"""
        return ResponseWrapper.error_response(
            error_type="calculation",
            error_message=message,
            error_code=ERROR_CODES["CALCULATION_ERROR"],
            request_id=request_id,
            path=path,
            method=method
        )
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate unique request ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def extract_request_info(request: Request) -> Dict[str, str]:
        """Extract request information for logging"""
        return {
            "path": str(request.url.path),
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }


def add_response_metadata(response: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
    """Add standard metadata to any response"""
    if request_id:
        response["request_id"] = request_id
    
    response["timestamp"] = datetime.now().isoformat()
    response["version"] = APP_VERSION
    
    return response
