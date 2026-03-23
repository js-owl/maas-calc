"""
3D Printing price calculator
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException

from .base_calculator import BaseCalculator
from models.calculation_models import PrintingCalculationRequest
from models.response_models import UnifiedCalculationResponse
from calculations.core import calculate_cost

logger = logging.getLogger(__name__)


class PrintingCalculator(BaseCalculator):
    """3D Printing price calculator"""
    
    def __init__(self):
        super().__init__()
        self.service_id = "printing"
        self.calculation_method = "3D Printing Price Calculation"
    
    async def calculate(self, request: PrintingCalculationRequest) -> UnifiedCalculationResponse:
        """Calculate 3D printing price"""
        self._validate_request(request)
        self._log_calculation_start(request.file_id, "3D printing")
        
        try:
            # Import calculation functions from legacy main
            from calculations.printing import calculate_printing_price
            from utils.helpers import (
                get_material_info,
                get_location_info,
                get_cover_processing_info,
                get_tolerance_info,
                get_finish_info
            )
            
            # Prepare calculation parameters in the format expected by legacy functions
            calc_params = {
                "length": request.dimensions.length,
                "width": request.dimensions.width,
                "height": request.dimensions.height,
                "quantity": request.quantity,
                "material_id": request.material_id,
                "material_form": request.material_form,
                "k_type": request.k_type,
                "k_process": request.k_process,
                "cover_id": request.cover_id,
                "k_otk": request.k_otk,
                "k_cert": request.k_cert,
                "service_id": request.service_id
            }
            #logger.info(f"{calc_params}")
            # Perform calculation using existing logic
            result = calculate_printing_price(calc_params)

            # Calculate cover coefficient
            k_cover = self._calculate_cover_coefficient(request.cover_id)

            # get total_price_breakdown
            material_price = result.get("mat_price")
            work_price_full = result.get("work_price_full")
            location = getattr(request, 'location', 'location_3')
            _, price_bw = calculate_cost(
                material_price,
                work_price_full,
                location,
                breakdown=True
            )
            detail_price = result["detail_price"]
            total_price = detail_price * request.quantity
            price_bw["total_price (include quantity)"] = total_price
            price_bw["price_per_kg"] = result.get('material_price_per_kg', 0.0) # add to front display
            price_bw["dop_mat_price"] = result.get("work_price_breakdown", {}).get("base_work_price") * (k_cover - 1) # add to front display
            price_bw["mat_price_full"] = price_bw["mat_price"] + price_bw["dop_mat_price"] # add to front display
            price_bw["total_time"] = result.get("work_time") # add to front display
            price_bw["price_special_equipment_to_quantity"] = 0 # add to front display
            
            # Build response
            response_data = self._create_base_response(
                file_id=request.file_id,
                part_price=result["detail_price"],
                detail_price=detail_price,
                part_price_one=result["detail_price_one"],
                detail_price_one=result["detail_price_one"],
                total_price=result["total_price"],
                total_time=result["total_time"],
                mat_volume=result.get("mat_volume"),
                mat_weight=result.get("mat_weight"),
                mat_price=material_price,
                work_price=work_price_full,
                work_time=result.get("work_time"),
                k_quantity=result.get("k_quantity"),
                k_complexity=result.get("k_complexity"),
                k_cover=k_cover,
                manufacturing_cycle=result.get("manufacturing_cycle"),
                suitable_machines=result.get("suitable_machines"),
                extracted_dimensions=request.dimensions,
                work_price_breakdown=result.get("work_price_breakdown"),
                total_price_breakdown=price_bw,
            )
            
            self._log_calculation_complete(request.file_id, "3D printing")
            return UnifiedCalculationResponse(**response_data)
            
        except HTTPException as e:
            logger.error(f"Error in printing calculation for file_id {request.file_id}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error in printing calculation for file_id {request.file_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
