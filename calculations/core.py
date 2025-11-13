"""
Core calculation functions extracted from legacy main
"""

import math
import numpy as np
from typing import Dict, Any, Union, List
from fastapi import HTTPException
from constants import (
    MATERIALS, COST_STRUCTURE, COVER, CERT_COSTS, 
    CYCLE_TIME_DEFAULTS, ERROR_MESSAGES, MACHINES
)
from models.base_models import MaterialForm


def calculate_mat_volume(length: float, width: float, thickness: float) -> float:
    """Calculate material volume in cubic meters"""
    volume = 0.000000001 * length * width * thickness
    return round(volume, 10)


def calculate_mat_volume_cylindrical(length: float, dia: float) -> float:
    """Calculate material volume in cubic meters (cylindrical)"""
    volume = 0.000000001 * length * math.pi * dia * dia / 4
    return round(volume, 10)


def calculate_mat_volume_printing(length: float, width: float, thickness: float, sifting_machine=False) -> float:
    """Calculate material volume in cubic meters (for printing)"""
    if not sifting_machine:
        volume = 0.000000001 * length * width * thickness
    else:
        volume = 0.000000001 * (length + 30) * (width + 30) * (thickness + 30)
    return round(volume, 10)


def calculate_mat_weight(volume: float, density: float) -> float:
    """Calculate material weight in kg"""
    weight = volume * density
    return round(weight, 4)


def calculate_mat_price(weight: float, price_per_kg: float) -> float:
    """Calculate material price with 20% markup"""
    price = weight * price_per_kg * 1.2
    return round(price, 2)


def resolve_material(material_id: str, material_form: Union[str, MaterialForm], process: str) -> Dict[str, Any]:
    """Resolve material properties by id and form; validate form and process compatibility.
    Raises HTTPException 422 on invalid input."""
    if material_id not in MATERIALS:
        raise HTTPException(status_code=422, detail=f"Unknown material_id '{material_id}'. Use /materials to list options.")
    mat = MATERIALS[material_id]
    
    if process not in mat.get("applicable_processes", []):
        raise HTTPException(status_code=422, detail=f"Material '{material_id}' is not applicable to '{process}'. Allowed: {mat.get('applicable_processes', [])}.")
    
    form_key = material_form.value if isinstance(material_form, MaterialForm) else material_form
    if form_key not in mat["forms"]:
        raise HTTPException(status_code=422, detail=f"Form '{form_key}' not allowed for {material_id}. Allowed: {list(mat['forms'].keys())}.")
    
    if process not in mat["forms"][form_key].get("applicable_processes", []):
        raise HTTPException(status_code=422, detail=f"Form '{form_key}' not allowed for {material_id} in process '{process}'. Allowed: {mat['forms'][form_key].get('applicable_processes', [])}.")
    
    # Special validation for cnc-lathe
    if process == "cnc-lathe" and form_key not in ["rod", "bar", "tube"]:
        raise HTTPException(status_code=422, detail="cnc-lathe requires material_form to be 'rod', 'bar', or 'tube'.")
    
    price = mat["forms"][form_key]["price"]
    return {"price": price, "density": mat["density"], "k_handle": mat["k_handle"], "family": mat["family"]}


def calculate_work_price(weight: float, k_handle: float, n_dimensions: int, location: str) -> float:
    """Calculate work price based on weight and handling coefficient"""
    cost_structure = COST_STRUCTURE.get(location)
    k_p = n_dimensions / 3
    work_time = 10 + k_p * 5 + weight * 1000 * k_handle # minutes
    price = (work_time * cost_structure["price_of_hour"]) / 60
    return round(price, 3)


def calculate_work_time(weight: float, k_handle: float, n_dimensions: int) -> float:
    """Calculate work time in hours based on weight and handling coefficient"""
    k_p = n_dimensions / 3
    work_time = 10 + k_p * 5 + weight * 1000 * k_handle # minutes
    return round(work_time / 60, 3)


def calculate_k_complexity(n_dimensions: int) -> float:
    """Calculate complexity coefficient"""
    if n_dimensions <= 15:
        return 0.75
    elif n_dimensions <= 50:
        return 1.0
    elif n_dimensions > 50:
        return 1.25
    else:
        return 0.75


def calculate_k_quantity(quantity: int) -> float:
    """Calculate quantity discount coefficient"""
    if quantity < 21:
        return 1.0
    elif quantity < 101:
        return 0.95
    elif quantity < 501:
        return 0.85
    else:
        return 0.8


def calculate_printing_work_time(volume: float) -> float:
    """Calculate work time of printing process from liters per hour and volume in m3"""
    V = 6 # liter per hour
    machine_time = volume * 1e3 / V
    pzv_time = 2
    full_time = machine_time + pzv_time

    return round(full_time, 3)


def calculate_cost(
        mat_price: float, work_price: float, location: str,
        breakdown=False
) -> Any:
        """Calculate cost from material price and work price"""
        cost_structure = COST_STRUCTURE.get(location)
        
        dop_salary = cost_structure["dop_salary_coef"] * work_price
        insurance_price = cost_structure["insurance_coef"] * (dop_salary + work_price)
        overhead_expenses = cost_structure["overhead_expenses_coef"] * work_price
        administrative_expenses = cost_structure["administrative_expenses_coef"] * work_price
        net_cost = mat_price +\
            work_price +\
            dop_salary +\
            insurance_price +\
            overhead_expenses +\
            administrative_expenses
        profit = mat_price * cost_structure["profit_material"] + \
            (net_cost - mat_price) * cost_structure["other_profit"]
        cost = np.round(net_cost + profit, 2)

        price_of_hour_with_others = cost_structure["price_of_hour"] * np.sum([ # price of hour including overhead expenses to front display
            1, 
            cost_structure["dop_salary_coef"],
            cost_structure["dop_salary_coef"] * cost_structure["insurance_coef"],
            cost_structure["insurance_coef"],
            cost_structure["overhead_expenses_coef"],
            cost_structure["administrative_expenses_coef"]
        ])

        if breakdown==True:
            return cost, {
                    "location": location,
                    "mat_price": mat_price,
                    "price_of_hour": cost_structure["price_of_hour"],
                    "price_of_hour_with_others": price_of_hour_with_others,
                    "work_price": work_price,
                    "dop_salary": dop_salary,
                    "insurance_price": insurance_price,
                    "overhead_expenses": overhead_expenses,
                    "administrative_expenses": administrative_expenses,
                    "net_cost": net_cost,
                    "profit": profit,
                    "cost": cost,
                    "sum_costs_labor": net_cost - mat_price
                }
        
        return cost

def calculate_cover_coefficient(cover_id: list) -> float:
    """Calculate cover processing coefficient"""
    if not cover_id:
        return 1.0
    
    # Remove duplicates
    unique_covers = list(set(cover_id))
    
    total_coefficient = 1.0
    for cover_item in unique_covers:
        if cover_item in COVER:
            total_coefficient *= COVER[cover_item]["value"]
        else:
            return [ERROR_MESSAGES["unknown_cover_id"]]
    
    return total_coefficient

def calculate_cycle(cover_id: List[str], quantity: int, k_otk: float) -> float:
    """Calculate cycle (time in days) of manufacturing"""
    buying_material_time = CYCLE_TIME_DEFAULTS["buying_material_time"]
    developing_technology_time = CYCLE_TIME_DEFAULTS["developing_technology_time"]
    developing_program_time = CYCLE_TIME_DEFAULTS["developing_program_time"]
    preparing_material_time = CYCLE_TIME_DEFAULTS["preparing_material_time"]
    
    cycle = buying_material_time + developing_technology_time + developing_program_time + preparing_material_time
    
    # Add cover processing time
    for cover_item in cover_id:
        if cover_item in COVER:
            cycle += COVER[cover_item]["cycle_time"]
    
    # Add quantity-based time
    if quantity < 21:
        quantity_coef = 0
    elif quantity < 101:
        quantity_coef = 1
    elif quantity < 501:
        quantity_coef = 2
    else:
        quantity_coef = 3
    
    cycle += 1 + quantity_coef
    
    return cycle

def check_machines(part: dict, processing_type: str, location: str, mode="default") -> list:
    """Return list of machines for given part dimensions"""
    if any(k not in part or part[k] is None for k in ("length", "width", "thickness")):
        raise ValueError("Sizes of detail must contain 'length', 'width', 'thickness'. Also it all must not be None")
    
    suitable_machines = []
    
    if processing_type in ("cnc-milling", "printing", "milling"):
        processing_type = processing_type.replace("cnc-", "")
        part_sizes = sorted(part.values(), reverse=True)
        # Find suitable milling machines from MACHINES constant
        for machine_id, machine_info in MACHINES.items():
            if machine_info.get("type")==processing_type \
                and machine_info.get("location")==location:
                # Check if part fits in machine dimensions
                if (part_sizes[0] <= machine_info.get("max_x", float('inf')) and
                    part_sizes[1] <= machine_info.get("max_y", float('inf')) and
                    part_sizes[2] <= machine_info.get("max_z", float('inf'))):
                    suitable_machines.append(machine_info.get("name", machine_id))
    elif processing_type in ("lathe", "cnc-lathe"):
        processing_type = processing_type.replace("cnc-", "")
        # For lathe, we check if the part is roughly cylindrical
        x, y, z = part["length"], part["width"], part["thickness"]
        if abs(x - y) < max(x, y) * 0.1:  # Roughly cylindrical
            # Find suitable lathe machines from MACHINES constant
            for machine_id, machine_info in MACHINES.items():
                if machine_info.get("type") == processing_type \
                    and machine_info.get("location")==location:
                    # Check if part fits in machine dimensions
                    if (max(x, y) <= machine_info.get("max_diameter", float('inf')) and
                        z <= machine_info.get("max_length", float('inf'))):
                        suitable_machines.append(machine_info.get("name", machine_id))
        else:
            # Even if not cylindrical, try to find suitable lathe
            for machine_id, machine_info in MACHINES.items():
                if machine_info.get("type") == processing_type and \
                    machine_info.get("location")==location:
                    if (max(x, y) <= machine_info.get("max_diameter", float('inf')) and
                        z <= machine_info.get("max_length", float('inf'))):
                        suitable_machines.append(machine_info.get("name", machine_id))
    else:
        return [ERROR_MESSAGES["unknown_manufacturing"]]

    if not suitable_machines:
        return [ERROR_MESSAGES["no_suitable_machines"]]
    
    return suitable_machines

def get_material_info(material_id: str, material_form: str) -> Dict[str, Any]:
    """Extract material information for ML prediction"""
    # Get material properties
    material_data = MATERIALS.get(material_id, {})
    material_form_data = material_data["forms"].get(material_form, {})
    
    return {
        'material_bar': material_form,
        'material_name': material_data.get('material_name', 'unknown'),
        'material_name_main': material_data.get('material_name_main', 'unknown'),
        'material_group': material_data.get('material_group', 'unknown'),
        'material_name_group': material_data.get('material_name_group', 'unknown'),
        'material_coef': material_data.get('material_coef', 0.0),
        'hardness': material_data.get('hardness', 0.0),
        'strenghtness': material_data.get('strenghtness', 0.0),
        'thermal_conductivity': material_data.get('thermal_conductivity', 0.0),
        'relative_coef': material_data.get('relative_coef', 0.0),
        'density': material_data.get('density', 0.0),
        'price': material_form_data.get('price', 0.0)
    }