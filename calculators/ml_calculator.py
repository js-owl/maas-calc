"""
ML-based Calculator for Manufacturing Price Calculations

This calculator uses ML models to predict work time and calculate prices
based on geometric features extracted from CAD files.
"""

import logging
import math
import re
import numpy as np
from typing import Dict, Any, Optional, Tuple
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

try:
    from constants import DOP_MATERIALS
except ImportError:  # Backward compatibility with older constants.py
    DOP_MATERIALS = {}
from calculations.core import (
    calculate_k_quantity, calculate_cost, calculate_cover_coefficient,
    calculate_cycle, check_machines, get_material_info, calculate_billable_material_weight
)

logger = logging.getLogger(__name__)


COMPOSITE_SPECIAL_EQUIPMENT_MATERIAL = "mdf"
COMPOSITE_SPECIAL_EQUIPMENT_FORM = "plate"
COMPOSITE_SPECIAL_EQUIPMENT_MARGIN = 1.2


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

    def _calculate_composite_special_equipment_material_costs(self, request: Any) -> Dict[str, Any]:
        """Calculate MDF technological tooling material cost for composite parts.

        The default assumption is a layered tooling blank made from MDF plates.
        The blank dimensions are the part OBB dimensions with a 20% reserve.
        DOP_MATERIALS["mdf"]["forms"]["plate"] is expected to provide:
        - price: price of one full plate;
        - sizes: three plate dimensions in mm, separated by "x".
        """
        default_response = {
            "special_equipment_material_id": COMPOSITE_SPECIAL_EQUIPMENT_MATERIAL,
            "special_equipment_material_form": COMPOSITE_SPECIAL_EQUIPMENT_FORM,
            "special_equipment_plate_price": 0.0,
            "special_equipment_plate_sizes_mm": None,
            "special_equipment_blank_dimensions_mm": None,
            "special_equipment_layer_count": 0,
            "special_equipment_pieces_per_plate": 0,
            "special_equipment_required_volume_mm3": 0.0,
            "special_equipment_plate_volume_mm3": 0.0,
            "special_equipment_plate_volume_fraction": 0.0,
            "special_equipment_pricing_mode": None,
            "special_equipment_plates_needed": 0.0,
            "material_price_special_equipment": 0.0,
        }

        try:
            form_data = (
                DOP_MATERIALS
                .get(COMPOSITE_SPECIAL_EQUIPMENT_MATERIAL, {})
                .get("forms", {})
                .get(COMPOSITE_SPECIAL_EQUIPMENT_FORM, {})
            )
            if not form_data:
                raise ValueError(
                    "DOP_MATERIALS['mdf']['forms']['plate'] is not configured"
                )

            plate_price = float(form_data.get("price", 0.0) or 0.0)
            if plate_price <= 0:
                raise ValueError("MDF plate price must be greater than zero")

            plate_x, plate_y, plate_z = self._parse_plate_sizes_mm(form_data.get("sizes"))
            part_x, part_y, part_z = self._get_request_obb_dimensions_mm(request)

            blank_x = part_x * COMPOSITE_SPECIAL_EQUIPMENT_MARGIN
            blank_y = part_y * COMPOSITE_SPECIAL_EQUIPMENT_MARGIN
            blank_z = part_z * COMPOSITE_SPECIAL_EQUIPMENT_MARGIN

            # Treat MDF as a sheet material: two largest dimensions are the sheet plane,
            # the smallest dimension is the layer thickness.
            plate_plane_x, plate_plane_y, plate_thickness = sorted(
                [plate_x, plate_y, plate_z],
                reverse=True,
            )
            blank_plane_x, blank_plane_y, blank_height = sorted(
                [blank_x, blank_y, blank_z],
                reverse=True,
            )

            # Number of MDF layers needed to build the tooling blank height.
            # Example: for a 24 mm tooling blank and a 10 mm MDF plate we need
            # three physical layers in the sandwich.
            layer_count = max(1, int(math.ceil(blank_height / plate_thickness)))

            # Required material volume is calculated from the real tooling blank,
            # not from a rounded full-plate purchase quantity. This is important
            # for small composite parts: if the tooling blank consumes less than
            # one MDF plate, the material cost must be proportional to the used
            # plate volume instead of being clamped to the full plate price.
            required_volume_mm3 = blank_plane_x * blank_plane_y * blank_height
            plate_volume_mm3 = plate_plane_x * plate_plane_y * plate_thickness
            plate_volume_fraction = required_volume_mm3 / plate_volume_mm3

            pieces_per_plate = self._calculate_rectangular_pieces_per_plate(
                plate_plane_x,
                plate_plane_y,
                blank_plane_x,
                blank_plane_y,
            )

            # Convert plate price to a volume price and charge only the consumed
            # MDF volume when the tooling fits inside a single plate. In other
            # words: material_price = plate_price / plate_volume * required_volume.
            # The pieces_per_plate check prevents underpricing flat blanks whose
            # volume is below one plate, but whose footprint is larger than a plate.
            if plate_volume_fraction <= 1.0 and pieces_per_plate > 0:
                plates_needed = plate_volume_fraction
                pricing_mode = "volume_fraction"
                material_price_special_equipment = round(plate_price * plate_volume_fraction, 2)
            else:
                # For blanks larger than one plate, keep the previous conservative
                # full-plate nesting/tiling estimate: once the tooling exceeds one
                # plate by volume or footprint, fractional accounting can
                # underestimate waste.
                if pieces_per_plate > 0:
                    plates_needed = int(math.ceil(layer_count / pieces_per_plate))
                else:
                    # The tooling layer is larger than a plate. Use a simple tiling
                    # estimate and multiply it by the number of MDF layers.
                    plates_per_layer = self._calculate_plates_per_large_layer(
                        plate_plane_x,
                        plate_plane_y,
                        blank_plane_x,
                        blank_plane_y,
                    )
                    plates_needed = plates_per_layer * layer_count

                pricing_mode = "full_plate_tiling"
                material_price_special_equipment = round(plates_needed * plate_price, 2)

            return {
                **default_response,
                "special_equipment_plate_price": plate_price,
                "special_equipment_plate_sizes_mm": {
                    "x": plate_x,
                    "y": plate_y,
                    "z": plate_z,
                },
                "special_equipment_blank_dimensions_mm": {
                    "x": round(blank_x, 4),
                    "y": round(blank_y, 4),
                    "z": round(blank_z, 4),
                },
                "special_equipment_layer_count": layer_count,
                "special_equipment_pieces_per_plate": pieces_per_plate,
                "special_equipment_required_volume_mm3": round(required_volume_mm3, 4),
                "special_equipment_plate_volume_mm3": round(plate_volume_mm3, 4),
                "special_equipment_plate_volume_fraction": round(plate_volume_fraction, 8),
                "special_equipment_pricing_mode": pricing_mode,
                "special_equipment_plates_needed": round(plates_needed, 8),
                "material_price_special_equipment": material_price_special_equipment,
            }
        except Exception as e:
            logger.warning(f"Error calculating composite special equipment material costs: {e}")
            return {**default_response, "special_equipment_error": str(e)}

    def _parse_plate_sizes_mm(self, sizes: Any) -> Tuple[float, float, float]:
        """Parse plate sizes from strings like '1500x3000x16' or '1500х3000х16'."""
        if not sizes:
            raise ValueError("MDF plate sizes are empty")

        parts = [
            part.strip().replace(",", ".")
            for part in re.split(r"[xх×*]", str(sizes).lower())
            if part.strip()
        ]
        if len(parts) != 3:
            raise ValueError(f"MDF plate sizes must contain exactly 3 dimensions: {sizes!r}")

        values = tuple(float(part) for part in parts)
        if any(value <= 0 for value in values):
            raise ValueError(f"MDF plate sizes must be positive: {sizes!r}")
        return values

    def _get_request_obb_dimensions_mm(self, request: Any) -> Tuple[float, float, float]:
        """Get OBB dimensions from request attributes, ML features or dimensions fallback."""
        ml_features = getattr(request, "ml_features", {}) or {}

        def _get_dim(name: str) -> Optional[float]:
            value = getattr(request, name, None)
            if value is None:
                value = ml_features.get(name)
            if value is None:
                return None
            try:
                value = float(value)
            except (TypeError, ValueError):
                return None
            return value if value > 0 else None

        obb_x = _get_dim("obb_x")
        obb_y = _get_dim("obb_y")
        obb_z = _get_dim("obb_z")
        if obb_x and obb_y and obb_z:
            return obb_x, obb_y, obb_z

        dimensions = getattr(request, "dimensions", None) or ml_features.get("dimensions")
        if isinstance(dimensions, dict):
            values = (
                dimensions.get("length"),
                dimensions.get("width"),
                dimensions.get("height"),
            )
        else:
            values = (
                getattr(dimensions, "length", None),
                getattr(dimensions, "width", None),
                getattr(dimensions, "height", None),
            )

        try:
            parsed = tuple(float(value) for value in values)
        except (TypeError, ValueError):
            raise ValueError("Cannot determine part OBB dimensions for composite special equipment")

        if len(parsed) != 3 or any(value <= 0 for value in parsed):
            raise ValueError("Part OBB dimensions must be positive")
        return parsed

    def _calculate_rectangular_pieces_per_plate(
        self,
        plate_x: float,
        plate_y: float,
        blank_x: float,
        blank_y: float,
    ) -> int:
        """Estimate how many rectangular blank layers fit into one plate."""
        count_normal = math.floor(plate_x / blank_x) * math.floor(plate_y / blank_y)
        count_rotated = math.floor(plate_x / blank_y) * math.floor(plate_y / blank_x)
        return max(int(count_normal), int(count_rotated), 0)

    def _calculate_plates_per_large_layer(
        self,
        plate_x: float,
        plate_y: float,
        blank_x: float,
        blank_y: float,
    ) -> int:
        """Estimate how many full plates are needed when one layer exceeds plate size."""
        count_normal = math.ceil(blank_x / plate_x) * math.ceil(blank_y / plate_y)
        count_rotated = math.ceil(blank_x / plate_y) * math.ceil(blank_y / plate_x)
        return max(1, int(min(count_normal, count_rotated)))

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

            # For composite parts the need for tooling is not predicted by a classifier.
            # The frontend sends this flag explicitly. Any value except 1 is treated as 0
            # to keep the old calculation path unchanged by default.

            is_need_special_equipment = int(getattr(request, 'is_need_special_equipment', 0) or 0)
            is_need_special_equipment = 1 if is_need_special_equipment == 1 else 0

            if is_need_special_equipment:
                # Tooling material for composite parts is MDF plate by default.
                # The helper below calculates only the material part of the tooling:
                # part OBB -> +20% reserve -> MDF layered blank -> MDF material cost.
                special_equipment_material_costs = self._calculate_composite_special_equipment_material_costs(request)
                if special_equipment_material_costs.get('special_equipment_error'):
                    raise ValueError(special_equipment_material_costs['special_equipment_error'])
            else:
                # Keep a zero tooling block in the response so the frontend can read
                # the same keys regardless of the flag value.
                special_equipment_material_costs = {
                    'special_equipment_material_id': COMPOSITE_SPECIAL_EQUIPMENT_MATERIAL,
                    'special_equipment_material_form': COMPOSITE_SPECIAL_EQUIPMENT_FORM,
                    'special_equipment_plates_needed': 0.0,
                    'material_price_special_equipment': 0.0,
                }

            # Tooling labor heuristic is shared with metal CNC logic:
            # tooling_hours = part_predicted_hours * SPECIAL_EQUIPMENT_COEF.
            predicted_hours_special_equipment = (
                float(predicted_hours) * is_need_special_equipment * SPECIAL_EQUIPMENT_COEF
            )
            work_price_special_equipment = predicted_hours_special_equipment * price_of_hour

            # If tooling is disabled, material cost is explicitly multiplied by 0.
            # This protects the old composite calculation path from any accidental
            # non-zero defaults in DOP_MATERIALS.
            material_price_special_equipment = (
                float(special_equipment_material_costs.get('material_price_special_equipment', 0.0) or 0.0)
                * is_need_special_equipment
            )
            price_special_equipment = calculate_cost(
                material_price_special_equipment,
                work_price_special_equipment,
                location
            )

            # Tooling is a batch-level cost; distribute it across requested quantity
            # in the same way as the CNC milling special-equipment cost.
            price_special_equipment_to_quantity = price_special_equipment / quantity

            part_price, price_bw = calculate_cost(
                material_price,
                work_price_full,
                location,
                breakdown=True
            )
            detail_price = part_price + price_special_equipment_to_quantity
            price_bw["detail_price (include special_equipment)"] = detail_price

            part_price_one = calculate_cost(
                material_price,
                work_price_full_one,
                location
            )
            detail_price_one = part_price_one + price_special_equipment_to_quantity
            total_price = detail_price * quantity

            material_costs.update(special_equipment_material_costs)
            material_costs['is_need_special_equipment'] = is_need_special_equipment

            price_bw['mat_price_full'] = price_bw.get('mat_price', material_price)
            price_bw['total_time'] = float(predicted_hours)
            price_bw['total_price (include quantity)'] = total_price
            price_bw['is_need_special_equipment'] = is_need_special_equipment
            price_bw['material_price_special_equipment'] = material_price_special_equipment
            price_bw['price_special_equipment'] = price_special_equipment
            price_bw['price_special_equipment_to_quantity'] = price_special_equipment_to_quantity

            manufacturing_cycle = calculate_cycle(cover_id, quantity, k_otk)

            # calculation of one detail for front
            detail_price_calculation = self._calculate_detail_calculation(
                location,
                detail_price_one,
                material_price,
                price_special_equipment_to_quantity
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
