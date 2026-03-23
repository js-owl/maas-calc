"""
3D Printing calculation functions
"""

import logging
from typing import Dict, Any
from .core import (
    resolve_material, calculate_mat_volume, calculate_mat_weight, 
    calculate_mat_price, calculate_work_price, calculate_work_time,
    calculate_k_quantity, calculate_k_complexity, calculate_cost, calculate_cycle,
    check_machines, calculate_printing_work_time
)
from constants import CERT_COSTS, COVER, DEFAULTS, COST_STRUCTURE

logger = logging.getLogger(__name__)

def _calculate_cover_coefficient(cover_id: list) -> float:
    """Calculate cover processing coefficient (multiplicative)"""
    if not cover_id:
        return 1.0
    
    # Remove duplicates
    unique_covers = list(set(cover_id))
    
    # Get cover coefficients from constants
    total_coefficient = 1.0
    
    for cover_id in unique_covers:
        if cover_id in COVER:
            total_coefficient *= COVER[cover_id]["value"]
        else:
            print(f"Warning: Unknown cover processing ID: {cover_id}")
    
    return total_coefficient


def calculate_printing_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate 3D printing price"""
    location = "location_3" # only this place has printers

    length = request_data["length"]
    width = request_data["width"]
    height = request_data["height"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    cover_id = request_data.get("cover_id", DEFAULTS["cover_id_list"])
    k_otk = float(request_data.get("k_otk", DEFAULTS["k_otk"]))
    k_cert = request_data.get("k_cert", DEFAULTS["k_cert_printing"])
    service_id = request_data.get("service_id", "unknown")
    
    part_sizes = {
        "length": length,
        "width": width,
        "height": height
    }
    suitable_machines = check_machines(part_sizes, service_id, location)

    material_props = resolve_material(material_id, material_form, process=service_id)
    
    reserve = 30
    mat_volume = calculate_mat_volume(
        length+reserve, width+reserve, height+reserve
    ) # м3
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])

    price_of_hour = COST_STRUCTURE.get(location)["price_of_hour"]
    work_time = calculate_printing_work_time(mat_volume)
    work_price = work_time * price_of_hour

    k_quantity = calculate_k_quantity(quantity)
    k_cover = _calculate_cover_coefficient(cover_id)

    #cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)
    
    # Calculate work price with all coefficients for full quantity
    work_price_full = work_price * k_cover * k_otk * k_quantity
    
    # Calculate work price for one detail (quantity = 1)
    work_price_full_one = work_price * k_cover * k_otk * 1.0
    
    # Calculate final prices using cost structure
    detail_price = calculate_cost(mat_price, work_price_full, location)
    detail_price_one = calculate_cost(mat_price, work_price_full_one, location)
    
    # Calculate manufacturing cycle
    manufacturing_cycle = calculate_cycle(cover_id, quantity, k_otk)
    
    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = work_time * quantity
    
    # work price breakdown
    work_price_breakdown={
        'base_work_price': work_price,
        'k_quantity': k_quantity,
        'k_cover': k_cover,
        'k_otk': k_otk,
        'k_tolerance': 0,
        'k_finish': 0,
        'final_work_price': work_price_full
    }
    return {
        "part_price": round(detail_price, 0),
        "detail_price": round(detail_price, 0),
        "part_price_one": round(detail_price_one, 0),
        "detail_price_one": round(detail_price_one, 0),
        "total_price": round(total_price, 0),
        "total_time": round(total_time, 3),
        "mat_volume": mat_volume,
        "mat_weight": mat_weight,
        "mat_price": mat_price,
        "work_price_full": work_price_full,
        "work_time": work_time,
        "k_quantity": k_quantity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines,
        "material_price_per_kg": material_props["price"],
        "work_price_breakdown": work_price_breakdown
    }
