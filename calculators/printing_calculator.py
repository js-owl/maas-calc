"""
3D Printing price calculator
"""

import logging
from typing import Dict, Any
from fastapi import HTTPException

from .base_calculator import BaseCalculator
from models.calculation_models import PrintingCalculationRequest
from models.response_models import UnifiedCalculationResponse
from calculations.core import build_unified_unit_price
from commercial_constants import COST_STRUCTURE
from constants import PRINTING_LOCATION

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
            from calculations.printing import calculate_printing_price

            # Prepare calculation parameters for the printing formula module.
            calc_params = {
                "length": request.dimensions.length,
                "width": request.dimensions.width,
                "height": request.dimensions.height,
                "quantity": request.quantity,
                "material_id": request.material_id,
                "material_form": request.material_form,
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

            # Unified pricing pipeline: calculate_cost first, then add tooling,
            # then apply k_quantity to the whole unit price.
            material_price = result.get("mat_price")
            work_price_breakdown = result.get("work_price_breakdown", {}) or {}
            base_work_price = float(work_price_breakdown.get("base_work_price") or 0.0)
            k_otk = float(request.k_otk or 1.0)
            k_cover = self._calculate_cover_coefficient(request.cover_id)
            work_price_without_quantity = base_work_price * k_cover * k_otk
            location = PRINTING_LOCATION  # only this place has printers
            price_special_equipment_to_quantity = 0.0
            unified_price = build_unified_unit_price(
                mat_price=material_price,
                work_price=work_price_without_quantity,
                location=location,
                quantity=request.quantity,
                k_quantity=result.get("k_quantity"),
                price_special_equipment_to_quantity=price_special_equipment_to_quantity,
            )

            detail_price = unified_price["detail_price"]
            detail_price_one = unified_price["detail_price_one"]
            total_price = unified_price["total_price"]
            price_bw = unified_price["total_price_breakdown"]
            material_usage = result.get("material_usage", {}) or {}
            price_bw["price_per_kg"] = result.get('material_price_per_kg', 0.0)
            price_bw["minimum_order_quantity_kg"] = material_usage.get("minimum_order_quantity_kg")
            price_bw["minimum_order_quantity_applied"] = material_usage.get("minimum_order_quantity_applied", False)
            price_bw["raw_estimated_weight_kg"] = result.get("raw_mat_weight", 0.0)
            price_bw["billable_weight_kg"] = result.get("mat_weight", 0.0)
            price_bw["billable_order_weight_kg"] = material_usage.get("billable_order_weight_kg", 0.0)
            price_bw["raw_order_weight_kg"] = material_usage.get("raw_order_weight_kg", 0.0)
            price_bw["total_time"] = result.get("work_time")
            price_bw["price_special_equipment_to_quantity"] = price_special_equipment_to_quantity
            price_bw["mat_price_full"] = price_bw["mat_price"]
            price_bw["dop_mat_price"] = 0.0

            work_price_breakdown["final_work_price"] = work_price_without_quantity
            work_price_breakdown["final_work_price_before_quantity"] = work_price_without_quantity
            work_price_breakdown["final_work_price_after_quantity"] = work_price_without_quantity * float(result.get("k_quantity") or 1.0)

            detail_price_calculation = unified_price["detail_price_calculation"]

            # Build response
            response_data = self._create_base_response(
                file_id=request.file_id,
                part_price=detail_price,
                detail_price=detail_price,
                part_price_one=detail_price_one,
                detail_price_one=detail_price_one,
                total_price=total_price,
                total_time=result["total_time"],
                mat_volume=result.get("mat_volume"),
                mat_weight=result.get("mat_weight"),
                mat_price=material_price,
                material_usage=material_usage,
                work_price=work_price_without_quantity,
                work_time=result.get("work_time"),
                k_quantity=result.get("k_quantity"),
                k_cover=k_cover,
                manufacturing_cycle=result.get("manufacturing_cycle"),
                suitable_machines=result.get("suitable_machines"),
                extracted_dimensions=request.dimensions,
                work_price_breakdown=work_price_breakdown,
                total_price_breakdown=price_bw,
                detail_price_calculation=detail_price_calculation
            )
            
            self._log_calculation_complete(request.file_id, "3D printing")
            return UnifiedCalculationResponse(**response_data)
            
        except HTTPException as e:
            logger.error(f"Error in printing calculation for file_id {request.file_id}: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error in printing calculation for file_id {request.file_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
