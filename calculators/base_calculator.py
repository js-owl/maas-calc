"""
Base calculator class for manufacturing calculations
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from models.response_models import UnifiedCalculationResponse
from models.calculation_models import (
    PrintingCalculationRequest,
    CNCMillingCalculationRequest,
    CNCLatheCalculationRequest,
    PaintingCalculationRequest
)

logger = logging.getLogger(__name__)


class BaseCalculator(ABC):
    """Base class for all manufacturing calculators"""
    
    def __init__(self):
        self.service_id = ""
        self.calculation_method = ""
    
    @abstractmethod
    async def calculate(self, request: Any) -> UnifiedCalculationResponse:
        """Calculate manufacturing price and return unified response"""
        pass
    
    def _create_base_response(
        self,
        file_id: str,
        filename: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create base response structure"""
        return {
            "file_id": file_id,
            "filename": filename,
            "service_id": self.service_id,
            "calculation_method": self.calculation_method,
            "timestamp": datetime.now().isoformat(),
            "message": "Calculation completed successfully",
            **kwargs
        }
    
    def _log_calculation_start(self, file_id: str, service_type: str) -> None:
        """Log calculation start"""
        logger.info(f"Calculating {service_type} price (file_id: {file_id})")
    
    def _log_calculation_complete(self, file_id: str, service_type: str) -> None:
        """Log calculation completion"""
        logger.info(f"Calculation completed for service: {service_type} (file_id: {file_id})")
    
    def _validate_request(self, request: Any) -> None:
        """Validate calculation request"""
        if not request:
            raise ValueError("Calculation request cannot be None")
        
        if not hasattr(request, 'file_id'):
            raise ValueError("Request must have file_id")
    
    def _calculate_cover_coefficient(self, cover_id: list) -> float:
        """Calculate cover processing coefficient (multiplicative)"""
        if not cover_id:
            return 1.0
        
        # Remove duplicates
        unique_covers = list(set(cover_id))
        
        # Get cover coefficients from constants
        from constants import COVER
        total_coefficient = 1.0
        
        for cover_id in unique_covers:
            if cover_id in COVER:
                total_coefficient *= COVER[cover_id]["value"]
            else:
                logger.warning(f"Unknown cover processing ID: {cover_id}")
        
        return total_coefficient
    
    def _calculate_cover_cycle_time(self, cover_id: list) -> float:
        """Calculate cover processing cycle time (additive)"""
        if not cover_id:
            return 0.0
        
        # Remove duplicates
        unique_covers = list(set(cover_id))
        
        # Get cover cycle times from constants
        from constants import COVER
        total_cycle_time = 0.0
        
        for cover_id in unique_covers:
            if cover_id in COVER:
                total_cycle_time += COVER[cover_id]["cycle_time"]
            else:
                logger.warning(f"Unknown cover processing ID: {cover_id}")
        
        return total_cycle_time
