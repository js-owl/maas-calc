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
from constants import COST_STRUCTURE

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
            material_usage = result.get("material_usage", {}) or {}
            price_bw["price_per_kg"] = result.get('material_price_per_kg', 0.0) # add to front display
            price_bw["minimum_order_quantity_kg"] = material_usage.get("minimum_order_quantity_kg")
            price_bw["minimum_order_quantity_applied"] = material_usage.get("minimum_order_quantity_applied", False)
            price_bw["raw_estimated_weight_kg"] = result.get("raw_mat_weight", 0.0)
            price_bw["billable_weight_kg"] = result.get("mat_weight", 0.0)
            price_bw["billable_order_weight_kg"] = material_usage.get("billable_order_weight_kg", 0.0)
            price_bw["raw_order_weight_kg"] = material_usage.get("raw_order_weight_kg", 0.0)
            price_bw["dop_mat_price"] = result.get("work_price_breakdown", {}).get("base_work_price") * (k_cover - 1) # add to front display
            price_bw["mat_price_full"] = price_bw["mat_price"] + price_bw["dop_mat_price"] # add to front display
            price_bw["total_time"] = result.get("work_time") # add to front display
            price_bw["price_special_equipment_to_quantity"] = 0 # add to front display
            
            # calculation of one detail for front
            price_special_equipment = 0 # TODO
            detail_price_calculation = self._calculate_detail_calculation(
                location,
                detail_price,
                material_price,
                price_special_equipment
            )

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
                material_usage=material_usage,
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

    def _calculate_detail_calculation(
            self, 
            location: str, 
            detail_price_one: float, 
            material_price: float,
            price_special_equipment: float
        ) -> Dict[str, Any]:
        "Calculation of one detail for front"

        profit_material = COST_STRUCTURE.get(location, {}).get('profit_material', 0)
        other_profit = COST_STRUCTURE.get(location, {}).get('other_profit', 0)
        salary_fund_with_taxes = round(float(
            float(detail_price_one) - material_price * float(1 + profit_material) - price_special_equipment * float(1 + other_profit)
            ) / float(1 + other_profit), 2)
        
        material_price_to_calc = round(material_price * float(1 + profit_material), 2)
        salary_fund_with_taxes_to_calc = round(salary_fund_with_taxes * float(1 + other_profit), 2)
        price_special_equipment_to_calc = round(price_special_equipment * float(1 + other_profit), 2)

        taxes = round(float(detail_price_one) * 0.22, 2)
        detail_price_calculation = {
            'material_price': material_price_to_calc,
            'salary_fund_with_taxes': salary_fund_with_taxes_to_calc,
            'price_special_equipment': price_special_equipment_to_calc,
            'detail_price_one': detail_price_one,
            'taxes': taxes,
            'detail_price_one_with_taxes': detail_price_one + taxes
        }

        return detail_price_calculation