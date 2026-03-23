"""
CNC Lathe price calculator
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException

from .base_calculator import BaseCalculator
from models.calculation_models import CNCLatheCalculationRequest
from models.response_models import UnifiedCalculationResponse

logger = logging.getLogger(__name__)


class CNCLatheCalculator(BaseCalculator):
    """CNC Lathe price calculator"""
    
    def __init__(self):
        super().__init__()
        self.service_id = "cnc-lathe"
        self.calculation_method = "CNC Lathe Price Calculation"
    
    async def calculate(self, request: CNCLatheCalculationRequest) -> UnifiedCalculationResponse:
        """Calculate CNC lathe price"""
        self._validate_request(request)
        self._log_calculation_start(request.file_id, "CNC lathe")
        
        try:
            # Import calculation functions from legacy main
            from calculations.cnc import calculate_cnc_lathe_price
            from utils.helpers import (
                get_material_info,
                get_location_info,
                get_cover_processing_info,
                get_tolerance_info,
                get_finish_info
            )
            
            # Prepare calculation parameters in the format expected by legacy functions
            # CNC lathe uses diameter instead of width/height
            calc_params = {
                "length": request.dimensions.length,
                "dia": request.dimensions.width,  # Use width as diameter for lathe
                "quantity": request.quantity,
                "material_id": request.material_id,
                "material_form": request.material_form,
                "cover_id": request.cover_id,
                "tolerance_id": request.tolerance_id,
                "finish_id": request.finish_id,
                "location": request.location,
                "k_otk": request.k_otk,
                "cnc_complexity": request.cnc_complexity,
                "cnc_setup_time": request.cnc_setup_time
            }
            
            # Perform calculation using existing logic
            result = calculate_cnc_lathe_price(calc_params)
            
            # Calculate cover coefficient
            k_cover = self._calculate_cover_coefficient(request.cover_id)
            
            # Calculate tolerance and finish coefficients from constants
            from constants import TOLERANCE, FINISH
            k_tolerance = TOLERANCE.get(request.tolerance_id, TOLERANCE["1"])['value']
            k_finish = FINISH.get(request.finish_id, FINISH["1"])['value']
            
            # Build response
            response_data = self._create_base_response(
                file_id=request.file_id,
                part_price=result["part_price"],
                detail_price=result["detail_price"],
                part_price_one=result["part_price_one"],
                detail_price_one=result["detail_price_one"],
                total_price=result["total_price"],
                total_time=result["total_time"],
                mat_volume=result.get("mat_volume"),
                mat_weight=result.get("mat_weight"),
                mat_price=result.get("mat_price"),
                work_price=result.get("work_price"),
                work_time=result.get("work_time"),
                k_quantity=result.get("k_quantity"),
                k_complexity=result.get("k_complexity"),
                k_cover=k_cover,
                k_tolerance=k_tolerance,
                k_finish=k_finish,
                manufacturing_cycle=result.get("manufacturing_cycle"),
                suitable_machines=result.get("suitable_machines"),
                cnc_complexity=request.cnc_complexity,
                cnc_setup_time=request.cnc_setup_time,
                extracted_dimensions=request.dimensions,
                used_parameters=calc_params
            )
            
            self._log_calculation_complete(request.file_id, "CNC lathe")
            return UnifiedCalculationResponse(**response_data)
            
        except HTTPException as e:
            logger.error(f"Error in CNC lathe calculation for file_id {request.file_id}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error in CNC lathe calculation for file_id {request.file_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
