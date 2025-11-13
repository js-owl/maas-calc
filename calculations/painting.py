"""
Painting calculation functions
"""

from typing import Dict, Any
from .core import resolve_material, calculate_k_quantity
from constants import PAINT_COEFFICIENTS, MATERIAL_PREP, PROCESS_COEFFICIENTS, CERT_COSTS, DEFAULTS, PAINT_PREP_BASE_COST


def calculate_base_paint_price(paint_area: float, paint_type: str) -> float:
    """Calculate base paint price per area"""
    paint_coeff = PAINT_COEFFICIENTS.get(paint_type, PAINT_COEFFICIENTS["acrylic"])
    base_price = paint_area * paint_coeff["base_price"] * paint_coeff["k_type"]
    return round(base_price, 2)


def calculate_preparation_cost(paint_area: float, material: str, paint_type: str) -> float:
    """Calculate preparation cost"""
    material_coeff = MATERIAL_PREP.get(material, MATERIAL_PREP["alum"])
    paint_coeff = PAINT_COEFFICIENTS.get(paint_type, PAINT_COEFFICIENTS["acrylic"])
    
    prep_cost = paint_area * PAINT_PREP_BASE_COST * material_coeff["k_clean"] * paint_coeff["k_prepare"]
    return round(prep_cost, 2)


def calculate_process_coefficient(paint_prepare: str, paint_primer: str, paint_lakery: str) -> float:
    """Calculate process coefficient based on preparation, primer, and lakery types"""
    prep_coeff = PROCESS_COEFFICIENTS["paint_prepare"].get(paint_prepare, 1.0)
    primer_coeff = PROCESS_COEFFICIENTS["paint_primer"].get(paint_primer, 1.0)
    lakery_coeff = PROCESS_COEFFICIENTS["paint_lakery"].get(paint_lakery, 1.0)
    
    return prep_coeff * primer_coeff * lakery_coeff


def calculate_painting_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate painting price"""
    paint_area = request_data["paint_area"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    paint_type = request_data["paint_type"]
    paint_prepare = request_data.get("paint_prepare", DEFAULTS["paint_prepare"])
    paint_primer = request_data.get("paint_primer", DEFAULTS["paint_primer"])
    paint_lakery = request_data.get("paint_lakery", DEFAULTS["paint_lakery"])
    k_cert = request_data.get("k_cert", DEFAULTS["k_cert_painting"])
    control_type = request_data.get("control_type", DEFAULTS["control_type"])
    
    base_paint_price = calculate_base_paint_price(paint_area, paint_type)
    props = resolve_material(material_id, material_form, process="painting")
    prep_cost = calculate_preparation_cost(paint_area, props["family"], paint_type)
    process_coeff = calculate_process_coefficient(paint_prepare, paint_primer, paint_lakery)
    cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)
    k_quantity = calculate_k_quantity(quantity)
    
    k_control = float(control_type) * 0.1 + 0.9
    
    total_base = (base_paint_price + prep_cost + cert_cost) * process_coeff
    detail_price = total_base * k_control * k_quantity
    
    # Calculate total price and total time (painting doesn't have work_time, so total_time = 0)
    total_price = detail_price * quantity
    total_time = 0.0  # Painting doesn't have work_time concept
    
    return {
        "part_price": round(detail_price, 0), # PLACEHOLDER
        "detail_price": round(detail_price, 0),
        "part_price_one": round(detail_price, 0), # PLACEHOLDER
        "detail_price_one": round(detail_price, 0),  # For painting, detail_price_one = detail_price
        "total_price": round(total_price, 0),
        "total_time": round(total_time, 3),
        "base_paint_price": base_paint_price,
        "prep_cost": prep_cost,
        "cert_cost": cert_cost,
        "process_coeff": process_coeff,
        "k_quantity": k_quantity,
        "k_control": k_control
    }
