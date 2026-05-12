"""
ML-based Calculator for Manufacturing Price Calculations

This calculator uses ML models to predict work time and calculate prices
based on geometric features extracted from CAD files.
"""

import logging
import math
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

from .base_calculator import BaseCalculator
from models.response_models import UnifiedCalculationResponse
from models.calculation_models import (
    PrintingCalculationRequest,
    CNCMillingCalculationRequest,
    CNCLatheCalculationRequest,
    PaintingCalculationRequest
)
from utils.ml_predictor import ml_predictor
from utils.composite_ml_predictor import composite_ml_predictor
from constants import (
    COST_STRUCTURE, MATERIALS, TOLERANCE, 
    FINISH, COVER, SPECIAL_EQUIPMENT_COEF, 
    SPECIAL_EQUIPMENT_MATERIAL, SPECIAL_EQUIPMENT_FORM
)
from calculations.core import (
    calculate_k_quantity, calculate_cost, calculate_cover_coefficient,
    calculate_cycle, check_machines, get_material_info, calculate_billable_material_weight
)

logger = logging.getLogger(__name__)


class MLCalculator(BaseCalculator):
    """ML-based calculator for manufacturing price calculations"""
    
    def __init__(self):
        super().__init__()
        self.service_id = "ml-prediction"
        self.calculation_method = "ML Model Prediction"
    
    async def calculate(self, request: Any) -> UnifiedCalculationResponse:
        """
        Calculate price using ML model prediction
        
        Args:
            request: Calculation request with file features
            
        Returns:
            Unified calculation response
        """
        try:
            self._log_calculation_start(request.file_id, "ML prediction")
            
            location = getattr(request, 'location', 'location_1')
            service_id = getattr(request, 'service_id', 'unknown')

            # Extract ML features from request
            ml_features = getattr(request, 'ml_features', None)
            if not ml_features:
                raise ValueError("No ML features provided for ML calculation")

            dimensions = ml_features.get('dimensions', None)

            # check suitable machines
            suitable_machines = check_machines(dimensions, service_id, location)

            # Get material information
            material_id = getattr(request, 'material_id', 'unknown')
            material_form = getattr(request, 'material_form', 'unknown')
            material_info = get_material_info(material_id, material_form)
            
            # Predict work time using ML model
            predicted_hours, is_need_special_equipment = ml_predictor.predict_from_file_features(
                ml_features, material_info
            )
            
            if predicted_hours is None or is_need_special_equipment is None:
                raise ValueError("ML predictions failed")

            # Calculate work price
            price_of_hour = COST_STRUCTURE.get(location, {}).get('price_of_hour', 0)
            work_price = predicted_hours * price_of_hour
            
            # Apply manufacturing coefficients
            quantity = getattr(request, 'quantity', 0)
            k_quantity = calculate_k_quantity(quantity)
            tolerance_id = getattr(request, 'tolerance_id', '4')
            k_tolerance = TOLERANCE.get(tolerance_id).get('value', 1.0)
            finish_id = getattr(request, 'finish_id', '3')
            k_finish = FINISH.get(finish_id).get('value', 1.0)

            # Get cover processing coefficient
            cover_id = getattr(request, 'cover_id', ['0'])
            k_cover = calculate_cover_coefficient(cover_id)
            
            # Get quality control coefficient
            k_otk = getattr(request, 'k_otk', 1.0)
            
            # Calculate final work price with quantity discount
            work_price_full = work_price * \
                k_cover * k_otk * k_quantity * k_tolerance * k_finish
            
            # Calculate work price for single unit (no quantity discount)
            work_price_full_one = work_price * \
                k_cover * k_otk * 1.0  * k_tolerance * k_finish # k_quantity=1.0
            
            # Calculate material costs
            material_costs = self._calculate_material_costs(request)
            material_price = material_costs['material_price']
            
            # Special equipment cost
            predicted_hours_special_equipment = predicted_hours * is_need_special_equipment * SPECIAL_EQUIPMENT_COEF
            work_price_special_equipment = predicted_hours_special_equipment * price_of_hour
            material_price_special_equipment = material_costs['material_price_special_equipment'] * is_need_special_equipment
            price_special_equipment = calculate_cost(
                material_price_special_equipment,
                work_price_special_equipment,
                location
            )

            # Calculate prices
            part_price, price_bw = calculate_cost(
                material_price,
                work_price_full,
                location,
                breakdown=True
            )
            price_special_equipment_to_quantity = price_special_equipment / quantity
            detail_price = part_price + price_special_equipment_to_quantity
            price_bw["detail_price (include special_equipment)"] = detail_price
            part_price_one = calculate_cost(
                material_price,
                work_price_full_one,
                location
            )
            detail_price_one = part_price_one + price_special_equipment_to_quantity
            total_price = detail_price * quantity
            price_bw["total_price (include quantity)"] = total_price
            
            price_bw["price_per_kg"] = material_costs.get('price_per_kg', 0.0) # add to front display
            price_bw["minimum_order_quantity_kg"] = material_costs.get('minimum_order_quantity_kg')
            price_bw["minimum_order_quantity_applied"] = material_costs.get('minimum_order_quantity_applied', False)
            price_bw["raw_estimated_weight_kg"] = material_costs.get('raw_estimated_weight_kg', 0.0)
            price_bw["billable_weight_kg"] = material_costs.get('billable_weight_kg', 0.0)
            price_bw["billable_order_weight_kg"] = material_costs.get('billable_order_weight_kg', 0.0)
            price_bw["raw_order_weight_kg"] = material_costs.get('raw_order_weight_kg', 0.0)
            price_bw["dop_mat_price"] = work_price * (k_cover - 1) # add to front display
            price_bw["mat_price_full"] = price_bw["mat_price"] + price_bw["dop_mat_price"] # add to front display
            price_bw["total_time"] = predicted_hours # add to front display
            price_bw["price_special_equipment_to_quantity"] = price_special_equipment_to_quantity # add to front display

            # Calculate manufacturing cycle
            manufacturing_cycle = calculate_cycle(cover_id, quantity, k_otk)
            
            # Calculation of one detail for front
            detail_price_calculation = self._calculate_detail_calculation(
                location,
                detail_price_one,
                material_price,
                price_special_equipment_to_quantity
            )

            # Create response
            response_data = self._create_base_response(
                file_id=request.file_id,
                filename=getattr(request, 'filename', None),
                part_price=part_price,
                detail_price=detail_price, 
                part_price_one=part_price_one, 
                detail_price_one=detail_price_one,  # Single unit price with special equipment
                total_price=total_price,
                total_time=predicted_hours,
                mat_volume=material_costs.get('volume', 0.0),
                mat_weight=material_costs.get('estimated_weight_kg', 0.0),
                mat_price=material_price,
                work_price=work_price_full_one, # with coefs
                k_quantity=k_quantity,
                k_cover=k_cover,
                k_tolerance=k_tolerance,
                k_finish=k_finish,
                k_otk=k_otk,
                manufacturing_cycle=manufacturing_cycle,
                suitable_machines=suitable_machines,
                extracted_dimensions=dimensions,
                calculation_engine="ml_model",
                ml_prediction_hours=predicted_hours,
                features_extracted=self._get_key_features(ml_features),
                material_costs=material_costs,
                work_price_breakdown={
                    'base_work_price': work_price,
                    'k_quantity': k_quantity,
                    'k_cover': k_cover,
                    'k_otk': k_otk,
                    'k_tolerance': k_tolerance,
                    'k_finish': k_finish,
                    'final_work_price': work_price_full
                },
                total_price_breakdown=price_bw,
                detail_price_calculation=detail_price_calculation
            )
            
            self._log_calculation_complete(request.file_id, "ML prediction")
            return UnifiedCalculationResponse(**response_data)
            
        except Exception as e:
            logger.error(f"Error in ML calculation for file_id {request.file_id}: {e}")
            raise
    
    def _calculate_material_costs(self, request: Any) -> Dict[str, Any]:
        """Calculate material costs using rule-based approach"""
        try:
            service_id = getattr(request, 'service_id', 'unknown')
            quantity = max(int(getattr(request, 'quantity', 1) or 1), 1)
            obb_x = getattr(request, 'obb_x', 0.0)
            obb_y = getattr(request, 'obb_y', 0.0)
            obb_z = getattr(request, 'obb_z', 0.0)
            material_id = getattr(request, 'material_id', 'unknown')
            material_form = getattr(request, 'material_form', 'unknown')

            material_data = get_material_info(material_id, material_form)
            price_per_kg = material_data['price'] # rub/kg
            density = material_data['density'] # kg/m3
            minimum_order_quantity = material_data.get('minimum_order_quantity')

            material_special_equipment_data = MATERIALS.get(SPECIAL_EQUIPMENT_MATERIAL, {})
            material_special_equipment_form_data = material_special_equipment_data["forms"].get(SPECIAL_EQUIPMENT_FORM, {})
            
            price_per_kg_special_equipment = material_special_equipment_form_data['price'] # rub/kg
            density_special_equipment = material_special_equipment_data['density'] # kg/m3
            
            if service_id=='cnc-milling' or service_id=='printing':
                volume = obb_x * obb_y * obb_z * 1.1 * 1e-9 # m3
                
            elif service_id=='cnc-lathe':
                volume = np.pi * obb_x * obb_y * obb_z / 4 * 1.1 * 1e-9 # m3
            else:
                volume = 0.0

            raw_weight = volume * density
            material_usage = calculate_billable_material_weight(
                raw_weight,
                quantity,
                minimum_order_quantity,
            )
            billable_weight = material_usage['billable_weight_per_unit_kg']
            material_price = round(billable_weight * price_per_kg, 2)
            material_price_special_equipment = round(volume * density_special_equipment * price_per_kg_special_equipment, 2) 

            return {
                'material_id': material_id,
                'volume': volume,
                'raw_estimated_weight_kg': round(raw_weight, 2), # kg per unit before MOQ
                'estimated_weight_kg': billable_weight, # kg per unit after order-level MOQ allocation
                'billable_weight_kg': billable_weight,
                'billable_order_weight_kg': material_usage['billable_order_weight_kg'],
                'raw_order_weight_kg': material_usage['raw_order_weight_kg'],
                'minimum_order_quantity_kg': material_usage['minimum_order_quantity_kg'],
                'minimum_order_quantity_applied': material_usage['minimum_order_quantity_applied'],
                'price_per_kg': price_per_kg,
                'material_price': material_price,
                'material_price_special_equipment': material_price_special_equipment
            }
            
        except Exception as e:
            logger.warning(f"Error calculating material costs: {e}")
            return {
                'material_id': 'unknown',
                'raw_estimated_weight_kg': 0.0,
                'estimated_weight_kg': 0.0,
                'billable_weight_kg': 0.0,
                'billable_order_weight_kg': 0.0,
                'raw_order_weight_kg': 0.0,
                'minimum_order_quantity_kg': None,
                'minimum_order_quantity_applied': False,
                'price_per_kg': 0.0,
                'material_price': 0.0,
                'material_price_special_equipment': 0.0
            }
    
    def _calculate_composite_material_costs(self, request: Any) -> Dict[str, Any]:
        """Calculate composite material consumption and cost by layers on a 1 m² base."""
        try:
            material_id = getattr(request, 'material_id', 'unknown')
            material_form = getattr(request, 'material_form', 'unknown')
            ml_features = getattr(request, 'ml_features', {}) or {}

            material_data = get_material_info(material_id, material_form)
            price_per_square_meter = float(material_data.get('price', 0.0) or 0.0)
            one_layer_thickness_mm = float(material_data.get('one_layer_thickness', 0.0) or 0.0)
            if one_layer_thickness_mm <= 0.0:
                raise ValueError('Composite material one_layer_thickness must be > 0')

            volume_mm3 = float(ml_features.get('volume', 0.0) or 0.0)
            volume_with_margin_mm3 = volume_mm3 * 1.1
            volume_m3 = volume_mm3 * 1e-9
            volume_with_margin_m3 = volume_with_margin_mm3 * 1e-9

            base_area_m2 = 1.0
            required_stack_thickness_m = volume_with_margin_m3 / base_area_m2
            one_layer_thickness_m = one_layer_thickness_mm * 1e-3
            layer_count = max(1, int(math.ceil(required_stack_thickness_m / one_layer_thickness_m))) if volume_with_margin_m3 > 0 else 0
            material_price = round(layer_count * price_per_square_meter, 2)

            return {
                'material_id': material_id,
                'base_area_m2': base_area_m2,
                'volume_m3': round(volume_m3, 9),
                'volume_with_margin_m3': round(volume_with_margin_m3, 9),
                'one_layer_thickness_mm': one_layer_thickness_mm,
                'required_stack_thickness_mm': round(required_stack_thickness_m * 1e3, 6),
                'layer_count': layer_count,
                'price_per_square_meter': price_per_square_meter,
                'material_price': material_price,
                'estimated_weight_kg': None,
            }
        except Exception as e:
            logger.warning(f"Error calculating composite material costs: {e}")
            return {
                'material_id': getattr(request, 'material_id', 'unknown'),
                'base_area_m2': 1.0,
                'volume_m3': 0.0,
                'volume_with_margin_m3': 0.0,
                'one_layer_thickness_mm': 0.0,
                'required_stack_thickness_mm': 0.0,
                'layer_count': 0,
                'price_per_square_meter': 0.0,
                'material_price': 0.0,
                'estimated_weight_kg': None,
            }

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

    def _get_key_features(self, ml_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key features for response.
        Discussible
        """
        try:
            return {
                'volume': ml_features.get('volume', 0.0),
                'surface_area': ml_features.get('surface_area', 0.0),
                'obb_dimensions': {
                    'x': ml_features.get('obb_x', 0.0),
                    'y': ml_features.get('obb_y', 0.0),
                    'z': ml_features.get('obb_z', 0.0)
                },
                'aspect_ratios': {
                    'xy': ml_features.get('aspect_ratio_xy', 1.0),
                    'yz': ml_features.get('aspect_ratio_yz', 1.0),
                    'xz': ml_features.get('aspect_ratio_xz', 1.0)
                },
                'complexity_metrics': {
                    'face_count': ml_features.get('features', {}).get('face_count', 0),
                    'vertex_count': ml_features.get('features', {}).get('vertex_count', 0),
                    'surface_entropy': ml_features.get('features', {}).get('surface_entropy', 0.0)
                },
                'lathe_suitable': bool(ml_features.get('check_sizes_for_lathe', 0))
            }
        except Exception as e:
            logger.warning(f"Error extracting key features: {e}")
            return {}


class MLPrintingCalculator(MLCalculator):
    """ML-based calculator for 3D printing"""
    
    def __init__(self):
        super().__init__()
        self.service_id = "printing"
        self.calculation_method = "3D Printing ML Prediction"


class MLCNCMillingCalculator(MLCalculator):
    """ML-based calculator for CNC milling"""
    
    def __init__(self):
        super().__init__()
        self.service_id = "cnc-milling"
        self.calculation_method = "CNC Milling ML Prediction"


class MLCNCLatheCalculator(MLCalculator):
    """ML-based calculator for CNC lathe"""
    
    def __init__(self):
        super().__init__()
        self.service_id = "cnc-lathe"
        self.calculation_method = "CNC Lathe ML Prediction"


class MLPaintingCalculator(MLCalculator):
    """ML-based calculator for painting"""
    
    def __init__(self):
        super().__init__()
        self.service_id = "painting"
        self.calculation_method = "Painting ML Prediction"


class MLCompositeCalculator(MLCalculator):
    """ML-based calculator for composite labor prediction."""

    def __init__(self):
        super().__init__()
        self.service_id = "composite"
        self.calculation_method = "Composite ML Prediction"

    async def calculate(self, request: Any) -> UnifiedCalculationResponse:
        try:
            self._log_calculation_start(request.file_id, "Composite ML prediction")
            ml_features = getattr(request, "ml_features", None)
            if not ml_features:
                raise ValueError("No ML features provided for composite calculation")

            material_id = getattr(request, "material_id", "unknown")
            material_form = getattr(request, "material_form", "unknown")
            material_info = get_material_info(material_id, material_form)

            predicted_hours = composite_ml_predictor.predict_from_file_features(
                ml_features,
                material_info,
            )
            if predicted_hours is None:
                raise ValueError("Composite ML prediction failed")

            location = getattr(request, 'location', 'location_1')
            quantity = max(int(getattr(request, 'quantity', 1) or 1), 1)
            cover_id = getattr(request, 'cover_id', ['0'])
            k_otk = float(getattr(request, 'k_otk', 1.0) or 1.0)

            price_of_hour = COST_STRUCTURE.get(location, {}).get('price_of_hour', 0)
            work_price = float(predicted_hours) * price_of_hour
            k_quantity = calculate_k_quantity(quantity)
            k_cover = calculate_cover_coefficient(cover_id)

            work_price_full = work_price * k_cover * k_otk * k_quantity
            work_price_full_one = work_price * k_cover * k_otk

            material_costs = self._calculate_composite_material_costs(request)
            material_price = float(material_costs.get('material_price', 0.0) or 0.0)

            part_price, price_bw = calculate_cost(
                material_price,
                work_price_full,
                location,
                breakdown=True
            )
            detail_price = part_price
            part_price_one = calculate_cost(
                material_price,
                work_price_full_one,
                location
            )
            detail_price_one = part_price_one
            total_price = detail_price * quantity

            price_bw['price_per_square_meter'] = material_costs.get('price_per_square_meter', 0.0)
            price_bw['one_layer_thickness_mm'] = material_costs.get('one_layer_thickness_mm', 0.0)
            price_bw['required_stack_thickness_mm'] = material_costs.get('required_stack_thickness_mm', 0.0)
            price_bw['layer_count'] = material_costs.get('layer_count', 0)
            price_bw['mat_price_full'] = price_bw.get('mat_price', material_price)
            price_bw['total_time'] = float(predicted_hours)
            price_bw['total_price (include quantity)'] = total_price

            manufacturing_cycle = calculate_cycle(cover_id, quantity, k_otk)

            # calculation of one detail for front
            price_special_equipment = 0 # TODO
            detail_price_calculation = self._calculate_detail_calculation(
                location,
                detail_price_one,
                material_price,
                price_special_equipment
            )
            response_data = self._create_base_response(
                file_id=request.file_id,
                filename=getattr(request, "filename", None),
                part_price=part_price,
                detail_price=detail_price,
                part_price_one=part_price_one,
                detail_price_one=detail_price_one,
                total_price=total_price,
                total_time=float(predicted_hours),
                mat_volume=material_costs.get('volume_with_margin_m3', 0.0),
                mat_weight=material_costs.get('estimated_weight_kg'),
                mat_price=material_price,
                work_price=work_price_full_one,
                work_time=float(predicted_hours),
                k_quantity=k_quantity,
                k_cover=k_cover,
                k_otk=k_otk,
                manufacturing_cycle=manufacturing_cycle,
                suitable_machines=None,
                extracted_dimensions=ml_features.get("dimensions"),
                calculation_engine="ml_model",
                ml_prediction_hours=float(predicted_hours),
                features_extracted=self._get_key_features(ml_features),
                material_costs=material_costs,
                work_price_breakdown={
                    'base_work_price': work_price,
                    'k_quantity': k_quantity,
                    'k_cover': k_cover,
                    'k_otk': k_otk,
                    'final_work_price': work_price_full,
                },
                total_price_breakdown=price_bw,
                detail_price_calculation=detail_price_calculation
            )
            self._log_calculation_complete(request.file_id, "Composite ML prediction")
            return UnifiedCalculationResponse(**response_data)
        except Exception as e:
            logger.error(f"Error in composite ML calculation for file_id {request.file_id}: {e}")
            raise
