"""
Standardized error response models
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ErrorDetail(BaseModel):
    """Individual error detail"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    value: Optional[Any] = Field(None, description="Value that caused the error")


class StandardErrorResponse(BaseModel):
    """Standardized error response format"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Main error message")
    error_code: str = Field(..., description="Error code for programmatic handling")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    path: Optional[str] = Field(None, description="API path that caused the error")
    method: Optional[str] = Field(None, description="HTTP method that caused the error")
    version: str = Field("3.1.0", description="API version")


class ValidationErrorResponse(StandardErrorResponse):
    """Validation error response"""
    error: str = Field("Validation Error", description="Validation error message")
    error_code: str = Field("VALIDATION_ERROR", description="Validation error code")


class FileProcessingErrorResponse(StandardErrorResponse):
    """File processing error response"""
    error: str = Field("File Processing Error", description="File processing error message")
    error_code: str = Field("FILE_PROCESSING_ERROR", description="File processing error code")


class CalculationErrorResponse(StandardErrorResponse):
    """Calculation error response"""
    error: str = Field("Calculation Error", description="Calculation error message")
    error_code: str = Field("CALCULATION_ERROR", description="Calculation error code")


class ServiceUnavailableErrorResponse(StandardErrorResponse):
    """Service unavailable error response"""
    error: str = Field("Service Unavailable", description="Service unavailable message")
    error_code: str = Field("SERVICE_UNAVAILABLE", description="Service unavailable error code")


class NotFoundErrorResponse(StandardErrorResponse):
    """Not found error response"""
    error: str = Field("Resource Not Found", description="Resource not found message")
    error_code: str = Field("NOT_FOUND", description="Not found error code")
