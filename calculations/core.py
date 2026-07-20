"""Core pricing helpers for active manufacturing calculation paths."""

import math
from contextvars import ContextVar
import numpy as np
from typing import Dict, Any, Union, List, Optional, Tuple
from fastapi import HTTPException
from commercial_constants import COST_STRUCTURE, MACHINES
from constants import (
    COVER,
    CYCLE_TIME_DEFAULTS, ERROR_MESSAGES,
    MATERIAL_MARKUP_RATE, PRINTING_VOLUME_SPEED_L_PER_HOUR,
    PRINTING_PREPARATION_TIME_HOURS,
    QUANTITY_DISCOUNT_CONTROL_POINTS, VAT_RATE,
)
from models.base_models import MaterialForm
from MATERIALS_gen import MATERIALS

# Optional per-request material catalog entry injected by API gateway
_material_snapshot_ctx: ContextVar[Optional[Tuple[str, Dict[str, Any]]]] = ContextVar(
    "material_snapshot", default=None
)


def set_material_snapshot(material_id: str, snapshot: Dict[str, Any]) -> None:
    _material_snapshot_ctx.set((material_id, snapshot))


def clear_material_snapshot() -> None:
    _material_snapshot_ctx.set(None)


def _lookup_material(material_id: str) -> Dict[str, Any]:
    override = _material_snapshot_ctx.get()
    if override and override[0] == material_id and isinstance(override[1], dict):
        return override[1]
    return MATERIALS.get(material_id, {})


def calculate_mat_volume(length: float, width: float, height: float) -> float:
    """Calculate material volume in cubic meters"""
    volume = 0.000000001 * length * width * height
    return round(volume, 10)



def calculate_mat_weight(volume: float, density: float) -> float:
    """Calculate material weight in kg"""
    weight = volume * density
    return round(weight, 4)


def calculate_mat_price(weight: float, price_per_kg: float) -> float:
    """Calculate material price with configured material markup."""
    price = weight * price_per_kg * (1 + MATERIAL_MARKUP_RATE)
    return round(price, 2)


def calculate_billable_material_weight(
    weight_per_unit_kg: float,
    quantity: int,
    minimum_order_quantity_kg: Any = None,
) -> Dict[str, Any]:
    """Return billable material weight with optional order-level MOQ.

    MOQ is applied once to the whole order and then distributed per unit,
    because the existing pricing flow calculates a per-unit price and later
    multiplies it by quantity.
    """
    safe_quantity = max(int(quantity or 1), 1)
    raw_weight_per_unit = max(float(weight_per_unit_kg or 0.0), 0.0)
    raw_order_weight = raw_weight_per_unit * safe_quantity

    try:
        moq = float(minimum_order_quantity_kg)
    except (TypeError, ValueError):
        moq = 0.0

    moq = moq if moq > 0 else None
    billable_order_weight = max(raw_order_weight, moq) if moq is not None else raw_order_weight

    return {
        "quantity": safe_quantity,
        "raw_weight_per_unit_kg": round(raw_weight_per_unit, 4),
        "raw_order_weight_kg": round(raw_order_weight, 4),
        "minimum_order_quantity_kg": moq,
        "minimum_order_quantity_applied": bool(moq is not None and raw_order_weight < moq),
        "billable_order_weight_kg": round(billable_order_weight, 4),
        "billable_weight_per_unit_kg": round(billable_order_weight / safe_quantity, 4),
    }



def _as_form_key(material_form: Union[str, MaterialForm, None]) -> Optional[str]:
    """Return a plain material form id from enum/string input."""
    if material_form is None:
        return None
    return material_form.value if isinstance(material_form, MaterialForm) else str(material_form)


def _is_form_applicable(form_info: Dict[str, Any], service_id: str = "") -> bool:
    """Return True when a material form can be used for the selected service."""
    processes = form_info.get("applicable_processes") or []
    return not service_id or not processes or service_id in processes


def resolve_priced_material_form(
    material_id: str,
    material_form: Union[str, MaterialForm, None],
    service_id: str = "",
) -> Optional[str]:
    """Resolve a material form that has a usable price for the service.

    The UI may send a stale/default form such as ``sheet`` for a material that
    is only priced as ``rod``. Pricing must not silently become zero in this
    case. The resolver prefers the requested form when it exists, is applicable
    to the service and has a positive price; otherwise it falls back to the
    first applicable form with a positive price.
    """
    material = _lookup_material(material_id)
    forms = material.get("forms") or {}
    if not forms:
        return None

    requested_form = _as_form_key(material_form)
    if requested_form in forms:
        requested_info = forms[requested_form] or {}
        if _is_form_applicable(requested_info, service_id):
            try:
                if float(requested_info.get("price") or 0.0) > 0.0:
                    return requested_form
            except (TypeError, ValueError):
                pass

    for form_id, form_info in forms.items():
        if not _is_form_applicable(form_info or {}, service_id):
            continue
        try:
            if float((form_info or {}).get("price") or 0.0) > 0.0:
                return form_id
        except (TypeError, ValueError):
            continue

    for form_id, form_info in forms.items():
        if _is_form_applicable(form_info or {}, service_id):
            return form_id

    return next(iter(forms.keys()), None)

def resolve_material(material_id: str, material_form: Union[str, MaterialForm], process: str) -> Dict[str, Any]:
    """Resolve material properties by id and form; validate form and process compatibility.
    Raises HTTPException 422 on invalid input."""
    material_data = _lookup_material(material_id)
    if not material_data and material_id not in MATERIALS:
        raise HTTPException(status_code=422, detail=f"Unknown material_id '{material_id}'. Use /materials to list options.")
    mat = material_data or MATERIALS[material_id]
    
    if process not in mat.get("applicable_processes", []):
        raise HTTPException(status_code=422, detail=f"Material '{material_id}' is not applicable to '{process}'. Allowed: {mat.get('applicable_processes', [])}.")
    
    form_key = material_form.value if isinstance(material_form, MaterialForm) else material_form
    if form_key not in mat["forms"]:
        raise HTTPException(status_code=422, detail=f"Form '{form_key}' not allowed for {material_id}. Allowed: {list(mat['forms'].keys())}.")
    
    if process not in mat["forms"][form_key].get("applicable_processes", []):
        raise HTTPException(status_code=422, detail=f"Form '{form_key}' not allowed for {material_id} in process '{process}'. Allowed: {mat['forms'][form_key].get('applicable_processes', [])}.")
    
    
    form_data = mat["forms"][form_key]
    price = form_data["price"]
    return {
        "price": price,
        "density": mat["density"],
        # "k_handle": mat["k_handle"],
        "family": mat["family"],
        "minimum_order_quantity": form_data.get(
            "minimum_order_quantity",
            mat.get("minimum_order_quantity"),
        ),
    }


def calculate_k_quantity(quantity: int) -> float:
    """Calculate quantity discount coefficient with log-space interpolation.

    The previous implementation used hard steps:
    <21 -> 1.00, <101 -> 0.95, <501 -> 0.85, otherwise -> 0.80.

    The new curve keeps approximately the same business control points,
    but removes price jumps at threshold quantities. The interpolation is
    linear over log(quantity), so every additional part has a smaller
    marginal discount effect than the previous one.
    """
    try:
        safe_quantity = max(int(quantity or 1), 1)
    except (TypeError, ValueError):
        safe_quantity = 1

    # Control points live in constants.py to keep business pricing knobs in one place.
    control_points = QUANTITY_DISCOUNT_CONTROL_POINTS

    if safe_quantity <= control_points[0][0]:
        return control_points[0][1]
    if safe_quantity >= control_points[-1][0]:
        return control_points[-1][1]

    log_q = math.log(safe_quantity)
    for (q0, k0), (q1, k1) in zip(control_points, control_points[1:]):
        if q0 <= safe_quantity <= q1:
            t = (log_q - math.log(q0)) / (math.log(q1) - math.log(q0))
            return round(k0 + (k1 - k0) * t, 4)

    return control_points[-1][1]


def calculate_printing_work_time(volume: float) -> float:
    """Calculate work time of printing process from liters per hour and volume in m3"""
    machine_time = volume * 1e3 / PRINTING_VOLUME_SPEED_L_PER_HOUR
    pzv_time = PRINTING_PREPARATION_TIME_HOURS
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
                    "work_price": work_price,
                    "dop_salary": dop_salary,
                    "insurance_price": insurance_price,
                    "overhead_expenses": overhead_expenses,
                    "administrative_expenses": administrative_expenses,
                    "net_cost": net_cost,
                    "profit": profit,
                    "cost": cost
                }
        
        return cost



def build_detail_price_calculation(
    *,
    location: str,
    price_breakdown: Dict[str, Any],
    detail_price: float,
    price_special_equipment_to_quantity: float = 0.0,
    k_quantity: float = 1.0,
) -> Dict[str, Any]:
    """Build the compact user-facing calculation for one priced detail.

    The compact calculation intentionally uses the final unit price after all
    service coefficients, distributed tooling cost and the quantity deflator.
    It groups the detailed ``calculate_cost`` lines into three readable
    buckets for the frontend:

    * material_price - material cost with material profit included;
    * salary_fund_with_taxes - all non-material production costs with labor
      profit included;
    * price_special_equipment - distributed tooling cost for one detail.
    """
    cost_structure = COST_STRUCTURE.get(location) or {}
    profit_material = float(cost_structure.get("profit_material", 0.0) or 0.0)
    other_profit = float(cost_structure.get("other_profit", 0.0) or 0.0)
    kq = float(k_quantity or 1.0)

    mat_price = float(price_breakdown.get("mat_price", 0.0) or 0.0)
    net_cost = float(price_breakdown.get("net_cost", 0.0) or 0.0)
    labor_net_cost = net_cost - mat_price
    equipment_unit_price = float(price_special_equipment_to_quantity or 0.0)

    material_price = round(mat_price * (1.0 + profit_material) * kq, 2)
    salary_fund_with_taxes = round(labor_net_cost * (1.0 + other_profit) * kq, 2)
    price_special_equipment = round(equipment_unit_price * kq, 2)

    price_without_vat = round(float(detail_price or 0.0), 2)
    taxes = round(price_without_vat * float(VAT_RATE), 2)
    total = round(price_without_vat + taxes, 2)

    return {
        "material_price": material_price,
        "salary_fund_with_taxes": salary_fund_with_taxes,
        "price_special_equipment": price_special_equipment,
        "price_without_vat": price_without_vat,
        "taxes": taxes,
        "total": total,
        "detail_price_one": price_without_vat, # to front display and backward compatibility
        "detail_price_one_with_taxes": total # to front display and backward compatibility
    }


def build_unified_unit_price(
    *,
    mat_price: float,
    work_price: float,
    location: str,
    quantity: int,
    k_quantity: float,
    price_special_equipment_to_quantity: float = 0.0,
) -> Dict[str, Any]:
    """Return the unified per-detail pricing structure for auto services.

    Order of operations:
    1. ``calculate_cost`` is applied to material and work cost without the
       quantity deflator.
    2. Distributed special tooling cost is added to one detail.
    3. ``k_quantity`` is applied to the whole one-detail price.
    """
    safe_quantity = max(int(quantity or 1), 1)
    kq = float(k_quantity or 1.0)
    equipment_unit_price = float(price_special_equipment_to_quantity or 0.0)

    base_cost, price_breakdown = calculate_cost(
        float(mat_price or 0.0),
        float(work_price or 0.0),
        location,
        breakdown=True,
    )
    base_cost = float(base_cost)
    detail_price_one = round(base_cost + equipment_unit_price, 2)
    detail_price = round(detail_price_one * kq, 2)
    total_price = round(detail_price * safe_quantity, 2)

    price_breakdown.update({
        "price_special_equipment_to_quantity": round(equipment_unit_price, 2),
        "detail_price": detail_price,
        "total_price (include quantity)": total_price,
    })

    detail_price_calculation = build_detail_price_calculation(
        location=location,
        price_breakdown=price_breakdown,
        detail_price=detail_price,
        price_special_equipment_to_quantity=equipment_unit_price,
        k_quantity=kq,
    )

    return {
        "base_cost": base_cost,
        "detail_price": detail_price,
        "detail_price_one": detail_price_one,
        "total_price": total_price,
        "total_price_breakdown": price_breakdown,
        "detail_price_calculation": detail_price_calculation,
    }


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
    """Return suitable machines for active machining/printing process types."""
    if any(k not in part or part[k] is None for k in ("length", "width", "height")):
        raise ValueError("Sizes of detail must contain 'length', 'width', 'height'. Also it all must not be None")

    if processing_type not in ("cnc-milling", "printing", "milling"):
        return [ERROR_MESSAGES["unknown_manufacturing"]]

    machine_type = processing_type.replace("cnc-", "")
    part_sizes = sorted(part.values(), reverse=True)
    suitable_machines = []
    for machine_id, machine_info in MACHINES.items():
        if machine_info.get("type") == machine_type and machine_info.get("location") == location:
            if (
                part_sizes[0] <= machine_info.get("max_x", float("inf"))
                and part_sizes[1] <= machine_info.get("max_y", float("inf"))
                and part_sizes[2] <= machine_info.get("max_z", float("inf"))
            ):
                suitable_machines.append(machine_info.get("name", machine_id))

    if not suitable_machines:
        return [ERROR_MESSAGES["no_suitable_machines"]]
    return suitable_machines

def get_material_info(material_id: str, material_form: str, service_id: str = "") -> Dict[str, Any]:
    """Extract material information for ML prediction and material pricing.

    When the requested form is missing/not priced, fall back to a priced form
    available for the selected service. This prevents cnc-milling requests from
    returning zero material price for materials that are priced as rod while the
    frontend sends the historical default form sheet.
    """
    material_data = _lookup_material(material_id)
    forms = material_data.get("forms") or {}
    requested_material_form = _as_form_key(material_form)
    resolved_material_form = resolve_priced_material_form(material_id, material_form, service_id) or requested_material_form
    material_form_data = forms.get(resolved_material_form, {})
    
    return {
        'material_bar': resolved_material_form,
        'requested_material_bar': requested_material_form,
        'material_form_fallback_applied': bool(resolved_material_form != requested_material_form),
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
        'family': material_data.get('family', 'unknown'),
        'price': material_form_data.get('price', 0.0),
        'one_layer_thickness': material_form_data.get('one_layer_thickness', 0.0),
        'minimum_order_quantity': material_form_data.get(
            'minimum_order_quantity',
            material_data.get('minimum_order_quantity')
        )
    }