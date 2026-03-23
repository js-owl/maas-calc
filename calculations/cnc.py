"""
CNC calculation functions (milling and lathe)
"""

from typing import Dict, Any
from .core import (
    resolve_material, calculate_mat_volume, calculate_mat_volume_cylindrical,
    calculate_mat_weight, calculate_mat_price, calculate_work_price, 
    calculate_work_time, calculate_k_quantity, calculate_k_complexity, 
    calculate_cost, calculate_cycle, check_machines
)
from constants import TOLERANCE, FINISH, CERT_COSTS, COVER, MACHINES, DEFAULTS, ERROR_MESSAGES


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

def calculate_cnc_milling_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate milling price"""
    location = DEFAULTS["location"]

    length = request_data["length"]
    width = request_data["width"]
    height = request_data["height"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    tolerance_id = request_data.get("tolerance_id", DEFAULTS["tolerance_id"])
    finish_id = request_data.get("finish_id", DEFAULTS["finish_id"])
    cover_id = request_data.get("cover_id", DEFAULTS["cover_id_list"])
    k_otk = float(request_data.get("k_otk", DEFAULTS["k_otk"]))
    k_cert = request_data.get("k_cert", DEFAULTS["k_cert_cnc"])        
    n_dimensions = request_data.get("n_dimensions", DEFAULTS["n_dimensions"])
    
    part_sizes = {
        "length": length,
        "width": width,
        "height": height
    }
    suitable_machines = check_machines(part_sizes, "milling", location)

    material_props = resolve_material(material_id, material_form, process="cnc-milling")
    
    mat_volume = calculate_mat_volume(length, width, height)
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])
    work_price = calculate_work_price(mat_weight, material_props["k_handle"], n_dimensions, location)
    work_time = calculate_work_time(mat_weight, material_props["k_handle"], n_dimensions)

    k_quantity = calculate_k_quantity(quantity)
    k_complexity = calculate_k_complexity(n_dimensions)

    k_tolerance = TOLERANCE.get(tolerance_id, TOLERANCE["1"])['value']
    k_finish = FINISH.get(finish_id, FINISH["1"])['value']
    # Calculate cover coefficient directly
    k_cover = _calculate_cover_coefficient(cover_id)

    cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)
    
    work_price_full = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        k_quantity
    )
    work_price_full_one_detail = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        1
    )

    detail_price = calculate_cost(mat_price + cert_cost, work_price_full, location)
    detail_price_one = calculate_cost(mat_price + cert_cost, work_price_full_one_detail, location)

    manufacturing_cycle = calculate_cycle(cover_id, quantity, k_otk)

    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = work_time * quantity

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
        "work_price": work_price_full,
        "work_time": work_time,
        "k_quantity": k_quantity,
        "k_complexity": k_complexity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines
    }


def calculate_cnc_lathe_price(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate CNC lathe price"""
    location = DEFAULTS["location"]

    length = request_data["length"]
    dia = request_data["dia"]
    quantity = request_data["quantity"]
    material_id = request_data["material_id"]
    material_form = request_data["material_form"]
    n_dimensions = request_data.get("n_dimensions", DEFAULTS["n_dimensions"])
    tolerance_id = request_data.get("tolerance_id", DEFAULTS["tolerance_id"])
    finish_id = request_data.get("finish_id", DEFAULTS["finish_id"])
    cover_id = request_data.get("cover_id", DEFAULTS["cover_id_list"])
    k_otk = float(request_data.get("k_otk", DEFAULTS["k_otk"]))
    k_cert = request_data.get("k_cert", DEFAULTS["k_cert_cnc"])

    part_sizes = {
        "length": dia,
        "width": dia,
        "height": length
    }
    suitable_machines = check_machines(part_sizes, "lathe", location)

    material_props = resolve_material(material_id, material_form, process="cnc-lathe")
    
    mat_volume = calculate_mat_volume_cylindrical(length, dia)
    mat_weight = calculate_mat_weight(mat_volume, material_props["density"])
    mat_price = calculate_mat_price(mat_weight, material_props["price"])
    work_price = calculate_work_price(mat_weight, material_props["k_handle"], n_dimensions, location)
    work_time = calculate_work_time(mat_weight, material_props["k_handle"], n_dimensions)

    k_quantity = calculate_k_quantity(quantity)
    k_complexity = calculate_k_complexity(n_dimensions)

    k_tolerance = TOLERANCE.get(tolerance_id, TOLERANCE["1"])['value']
    k_finish = FINISH.get(finish_id, FINISH["1"])['value']
    # Calculate cover coefficient directly
    k_cover = _calculate_cover_coefficient(cover_id)
    
    cert_cost = sum(CERT_COSTS.get(cert, 0) for cert in k_cert)

    work_price_full = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        k_quantity
    )
    work_price_full_one_detail = (
        work_price *
        k_complexity *
        k_tolerance *
        k_finish *
        k_cover *
        k_otk *
        1
    )

    detail_price = calculate_cost(mat_price + cert_cost, work_price_full, location)
    detail_price_one = calculate_cost(mat_price + cert_cost, work_price_full_one_detail, location)

    manufacturing_cycle = calculate_cycle(cover_id, quantity, k_otk)

    # Calculate total price and total time
    total_price = detail_price * quantity
    total_time = work_time * quantity

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
        "work_price": work_price_full,
        "work_time": work_time,
        "k_quantity": k_quantity,
        "k_complexity": k_complexity,
        "manufacturing_cycle": manufacturing_cycle,
        "suitable_machines": suitable_machines
    }
