"""
Data models for the manufacturing calculation API
"""

from .base_models import BaseModel, Dimensions, MaterialForm
from .request_models import UnifiedCalculationRequest
from .response_models import UnifiedCalculationResponse
from .calculation_models import (
    PrintingCalculationRequest,
    CNCMillingCalculationRequest, 
    CNCLatheCalculationRequest,
    PaintingCalculationRequest
)
from .error_models import (
    StandardErrorResponse,
    ValidationErrorResponse,
    FileProcessingErrorResponse,
    CalculationErrorResponse,
    ServiceUnavailableErrorResponse,
    NotFoundErrorResponse,
    ErrorDetail
)

__all__ = [
    "BaseModel",
    "Dimensions", 
    "MaterialForm",
    "UnifiedCalculationRequest",
    "UnifiedCalculationResponse",
    "PrintingCalculationRequest",
    "CNCMillingCalculationRequest",
    "CNCLatheCalculationRequest", 
    "PaintingCalculationRequest",
    "StandardErrorResponse",
    "ValidationErrorResponse",
    "FileProcessingErrorResponse",
    "CalculationErrorResponse",
    "ServiceUnavailableErrorResponse",
    "NotFoundErrorResponse",
    "ErrorDetail"
]
