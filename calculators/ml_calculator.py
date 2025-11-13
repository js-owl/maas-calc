"""
ML-based Calculator for Manufacturing Price Calculations

This calculator uses ML models to predict work time and calculate prices
based on geometric features extracted from CAD files.
"""

import logging
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
from constants import (
    COST_STRUCTURE, MATERIALS, TOLERANCE, 
    FINISH, COVER, SPECIAL_EQUIPMENT_COEF, 
    SPECIAL_EQUIPMENT_MATERIAL, SPECIAL_EQUIPMENT_FORM
)
from calculations.core import (
    calculate_k_quantity, calculate_cost, calculate_cover_coefficient,
    calculate_cycle, check_machines, get_material_info
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
            detail_price = part_price + price_special_equipment / quantity
            price_bw["detail_price (include special_equipment)"] = detail_price
            part_price_one = calculate_cost(
                material_price,
                work_price_full_one,
                location
            )
            detail_price_one = part_price_one + price_special_equipment
            total_price = detail_price * quantity
            price_bw["total_price (include quantity)"] = total_price
            
            price_bw["price_per_kg"] = material_costs.get('price_per_kg', 0.0) # add to front display
            price_bw["dop_mat_price"] = work_price * (k_cover - 1) # add to front display
            price_bw["mat_price_full"] = price_bw["mat_price"] + price_bw["dop_mat_price"] # add to front display
            price_bw["total_time"] = predicted_hours # add to front display
            price_bw["price_special_equipment_to_quantity"] = price_special_equipment / quantity # add to front display

            # Calculate manufacturing cycle
            manufacturing_cycle = calculate_cycle(cover_id, quantity, k_otk)
            
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
                total_price_breakdown=price_bw
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
            obb_x = getattr(request, 'obb_x', 0.0)
            obb_y = getattr(request, 'obb_y', 0.0)
            obb_z = getattr(request, 'obb_z', 0.0)
            material_id = getattr(request, 'material_id', 'unknown')
            material_form = getattr(request, 'material_form', 'unknown')

            material_data = get_material_info(material_id, material_form)
            price_per_kg = material_data['price'] # rub/kg
            density = material_data['density'] # kg/m3

            material_special_equipment_data = MATERIALS.get(SPECIAL_EQUIPMENT_MATERIAL, {})
            material_special_equipment_form_data = material_special_equipment_data["forms"].get(SPECIAL_EQUIPMENT_FORM, {})
            
            price_per_kg_special_equipment = material_special_equipment_form_data['price'] # rub/kg
            density_special_equipment = material_special_equipment_data['density'] # kg/m3
            
            if service_id=='cnc-milling' or service_id=='printing':
                volume = obb_x * obb_y * obb_z * 1.1 * 1e-9 # m3
                
            elif service_id=='cnc-lathe':
                volume = np.pi * obb_x * obb_y * obb_z / 4 * 1.1 * 1e-9 # m3

            material_price = round(volume * density * price_per_kg, 2)
            material_price_special_equipment = round(volume * density_special_equipment * price_per_kg_special_equipment, 2) 

            return {
                'material_id': material_id,
                'volume': volume,
                'estimated_weight_kg': round(volume * density, 2), # kg
                'price_per_kg': price_per_kg,
                'material_price': material_price,
                'material_price_special_equipment': material_price_special_equipment
            }
            
        except Exception as e:
            logger.warning(f"Error calculating material costs: {e}")
            return {
                'material_id': 'unknown',
                'estimated_weight_kg': 0.0,
                'price_per_kg': 0.0,
                'material_price': 0.0,
                'material_price_special_equipment': 0.0
            }
    
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
