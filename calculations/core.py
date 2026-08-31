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
    PRINTING_LOCATION, QUANTITY_DISCOUNT_CONTROL_POINTS, VAT_RATE,
    FINISH, TOLERANCE,
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


def lookup_material(material_id: str) -> Dict[str, Any]:
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
    material = lookup_material(material_id)
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
    material_data = lookup_material(material_id)
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


def recalculate_price_snapshot(
    payload: Dict[str, Any],
    changed_field: str,
) -> Dict[str, Any]:
    """Propagate one explicitly edited snapshot value toward its price totals.

    A complete snapshot contains duplicated values (for example ``mat_price``
    at the top level and in ``total_price_breakdown``), so the edited path must
    be explicit. Only dependent values are replaced; unrelated order metadata
    and service-specific fields are passed through unchanged.
    """
    result = dict(payload)
    breakdown = dict(result.get("total_price_breakdown") or {})
    compact = dict(result.get("detail_price_calculation") or {})
    result["total_price_breakdown"] = breakdown
    result["detail_price_calculation"] = compact

    path_parts = changed_field.split(".")
    if not path_parts or len(path_parts) > 2:
        raise ValueError(f"Unsupported changed_field: {changed_field!r}")

    source: Any = result
    for part in path_parts:
        if not isinstance(source, dict) or part not in source:
            raise ValueError(f"Unknown changed_field: {changed_field!r}")
        source = source[part]

    passthrough_fields = {
        "order_id",
        "order_name",
        "order_code",
        "manufacturing_cycle",
        "coating_thickness_microns",
        "electroplating_family",
        "electroplating_process_id",
        "processing_depth_microns",
        "special_instructions",
        "file_id",
        "document_ids",
    }
    if changed_field in passthrough_fields:
        return result

    if source is None:
        raise ValueError(f"changed_field {changed_field!r} cannot be null")

    def number(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    quantity = max(int(result.get("quantity") or 1), 1)
    service_id = str(result.get("service_id") or "")
    location = PRINTING_LOCATION if service_id == "printing" else "location_1"
    cost_structure = COST_STRUCTURE.get(location)
    if not cost_structure:
        raise ValueError(f"Cost structure is not configured for {location!r}")

    k_quantity = number(result.get("k_quantity"), calculate_k_quantity(quantity))
    mat_price = number(result.get("mat_price"), number(breakdown.get("mat_price")))
    work_price = number(result.get("work_price"), number(breakdown.get("work_price")))

    geometry_fields = {"length", "width", "height"}
    material_fields = {
        "material_id", "material_form", "mat_volume", "mat_weight", "mat_price",
        "total_price_breakdown.mat_price",
    }
    work_fields = {
        "total_time", "k_otk", "cover_id", "finish_id", "tolerance_id",
        "work_price", "total_price_breakdown.total_time",
        "total_price_breakdown.price_of_hour",
        "total_price_breakdown.work_price",
    }

    # Geometry/material is a small independent branch of the hierarchy.
    if changed_field in geometry_fields:
        dimensions = [result.get(name) for name in ("length", "width", "height")]
        if all(value is not None for value in dimensions):
            result["mat_volume"] = calculate_mat_volume(*(number(value) for value in dimensions))
            changed_field = "mat_volume"

    if changed_field in {"mat_volume", "material_id"}:
        material = lookup_material(str(result.get("material_id") or ""))
        density = number(material.get("density"))
        if density > 0:
            result["mat_weight"] = calculate_mat_weight(number(result.get("mat_volume")), density)
            changed_field = "mat_weight"

    if changed_field in {"mat_weight", "material_form"}:
        material_id = str(result.get("material_id") or "")
        form_id = resolve_priced_material_form(
            material_id,
            result.get("material_form"),
            service_id,
        )
        form = (lookup_material(material_id).get("forms") or {}).get(form_id or "", {})
        price_per_kg = number(form.get("price"))
        if price_per_kg > 0:
            result["mat_price"] = calculate_mat_price(
                number(result.get("mat_weight")),
                price_per_kg,
            )
            changed_field = "mat_price"

    if changed_field == "total_price_breakdown.mat_price":
        mat_price = number(breakdown.get("mat_price"))
        result["mat_price"] = mat_price
    elif changed_field == "mat_price":
        mat_price = number(result.get("mat_price"))
        breakdown["mat_price"] = mat_price

    # Time and manufacturing coefficients feed the per-detail work price.
    if changed_field == "total_time":
        breakdown["total_time"] = result.get("total_time")
    elif changed_field == "total_price_breakdown.total_time":
        result["total_time"] = breakdown.get("total_time")
    if changed_field == "total_price_breakdown.price_of_hour":
        price_of_hour = number(breakdown.get("price_of_hour"))
    else:
        price_of_hour = number(
            breakdown.get("price_of_hour"),
            number(cost_structure.get("price_of_hour")),
        )

    if changed_field in work_fields - {
        "work_price",
        "total_price_breakdown.work_price",
    }:
        time_value = number(
            breakdown.get("total_time"),
            number(result.get("total_time")),
        )
        coefficient = number(result.get("k_otk"), 1.0) or 1.0
        covers = result.get("cover_id") or []
        cover_coefficient = calculate_cover_coefficient(covers)
        if isinstance(cover_coefficient, (int, float)):
            coefficient *= float(cover_coefficient)
        if service_id == "cnc-milling":
            coefficient *= number(
                TOLERANCE.get(str(result.get("tolerance_id")), {}).get("value"),
                1.0,
            )
            coefficient *= number(
                FINISH.get(str(result.get("finish_id")), {}).get("value"),
                1.0,
            )
        work_price = time_value * price_of_hour * coefficient
        result["work_price"] = work_price
        breakdown["work_price"] = work_price
        changed_field = "work_price"
    elif changed_field == "total_price_breakdown.work_price":
        work_price = number(breakdown.get("work_price"))
        result["work_price"] = work_price
    elif changed_field == "work_price":
        work_price = number(result.get("work_price"))
        breakdown["work_price"] = work_price

    if changed_field == "quantity":
        k_quantity = calculate_k_quantity(quantity)
        result["k_quantity"] = k_quantity
    elif changed_field == "k_quantity":
        k_quantity = number(result.get("k_quantity"), 1.0)

    equipment_total = number(breakdown.get("price_special_equipment"))
    equipment_unit = number(breakdown.get("price_special_equipment_to_quantity"))
    if changed_field in {
        "is_need_special_equipment",
        "total_price_breakdown.is_need_special_equipment",
    }:
        need_equipment = bool(
            result.get("is_need_special_equipment")
            if changed_field == "is_need_special_equipment"
            else breakdown.get("is_need_special_equipment")
        )
        result["is_need_special_equipment"] = need_equipment
        breakdown["is_need_special_equipment"] = need_equipment
        if not need_equipment:
            equipment_total = 0.0
            equipment_unit = 0.0
    elif changed_field == "total_price_breakdown.material_price_special_equipment":
        if bool(breakdown.get("is_need_special_equipment", result.get("is_need_special_equipment"))):
            equipment_total = float(calculate_cost(
                number(breakdown.get("material_price_special_equipment")),
                0.0,
                location,
            ))
        else:
            equipment_total = 0.0
        equipment_unit = equipment_total / quantity
    elif changed_field == "total_price_breakdown.price_special_equipment":
        equipment_total = number(breakdown.get("price_special_equipment"))
        equipment_unit = equipment_total / quantity
    elif changed_field == "total_price_breakdown.price_special_equipment_to_quantity":
        equipment_unit = number(breakdown.get("price_special_equipment_to_quantity"))
        equipment_total = equipment_unit * quantity
    elif changed_field == "quantity" and equipment_total:
        equipment_unit = equipment_total / quantity

    breakdown["price_special_equipment"] = round(equipment_total, 2)
    breakdown["price_special_equipment_to_quantity"] = round(equipment_unit, 2)

    detailed_stage: Optional[str] = None
    if changed_field in material_fields:
        detailed_stage = "net"
    if changed_field in {"work_price", "total_price_breakdown.work_price"}:
        detailed_stage = "labor"
    if changed_field == "service_id":
        detailed_stage = "labor"
    if changed_field == "total_price_breakdown.dop_salary":
        detailed_stage = "insurance"
    if changed_field in {
        "total_price_breakdown.insurance_price",
        "total_price_breakdown.overhead_expenses",
        "total_price_breakdown.administrative_expenses",
    }:
        detailed_stage = "net"
    if changed_field == "total_price_breakdown.net_cost":
        detailed_stage = "profit"
    if changed_field == "total_price_breakdown.profit":
        detailed_stage = "cost"
    if changed_field == "total_price_breakdown.cost":
        detailed_stage = "unit"
    if changed_field in {
        "quantity", "k_quantity",
        "is_need_special_equipment",
        "total_price_breakdown.is_need_special_equipment",
        "total_price_breakdown.material_price_special_equipment",
        "total_price_breakdown.price_special_equipment",
        "total_price_breakdown.price_special_equipment_to_quantity",
    }:
        detailed_stage = "unit"

    stage_order = {
        "labor": 0,
        "insurance": 1,
        "net": 2,
        "profit": 3,
        "cost": 4,
        "unit": 5,
    }
    stage_index = stage_order.get(detailed_stage, 99)

    breakdown["mat_price"] = mat_price
    breakdown["work_price"] = work_price
    breakdown["price_of_hour"] = price_of_hour
    hour_multiplier = (
        1
        + number(cost_structure.get("dop_salary_coef"))
        + number(cost_structure.get("dop_salary_coef")) * number(cost_structure.get("insurance_coef"))
        + number(cost_structure.get("insurance_coef"))
        + number(cost_structure.get("overhead_expenses_coef"))
        + number(cost_structure.get("administrative_expenses_coef"))
    )
    if changed_field != "total_price_breakdown.price_of_hour_with_others":
        breakdown["price_of_hour_with_others"] = round(price_of_hour * hour_multiplier, 2)

    if stage_index <= stage_order["labor"]:
        breakdown["dop_salary"] = number(cost_structure.get("dop_salary_coef")) * work_price
        breakdown["overhead_expenses"] = number(cost_structure.get("overhead_expenses_coef")) * work_price
        breakdown["administrative_expenses"] = number(cost_structure.get("administrative_expenses_coef")) * work_price
    if stage_index <= stage_order["insurance"]:
        breakdown["insurance_price"] = number(cost_structure.get("insurance_coef")) * (
            work_price + number(breakdown.get("dop_salary"))
        )
    if stage_index <= stage_order["net"]:
        breakdown["net_cost"] = sum(number(breakdown.get(field)) for field in (
            "mat_price",
            "work_price",
            "dop_salary",
            "insurance_price",
            "overhead_expenses",
            "administrative_expenses",
        ))
    if stage_index <= stage_order["profit"]:
        net_cost = number(breakdown.get("net_cost"))
        breakdown["profit"] = (
            mat_price * number(cost_structure.get("profit_material"))
            + (net_cost - mat_price) * number(cost_structure.get("other_profit"))
        )
    if stage_index <= stage_order["cost"]:
        breakdown["cost"] = round(
            number(breakdown.get("net_cost")) + number(breakdown.get("profit")),
            2,
        )

    if stage_index <= stage_order["unit"]:
        detail_price_one = round(number(breakdown.get("cost")) + equipment_unit, 2)
        detail_price = round(detail_price_one * k_quantity, 2)
        result["detail_price_one"] = detail_price_one
        result["detail_price"] = detail_price
        result["total_price"] = round(detail_price * quantity, 2)
        breakdown["detail_price"] = detail_price
        compact = build_detail_price_calculation(
            location=location,
            price_breakdown=breakdown,
            detail_price=detail_price,
            price_special_equipment_to_quantity=equipment_unit,
            k_quantity=k_quantity,
        )
        result["detail_price_calculation"] = compact

    # Direct edits in the compact representation propagate only to its parents.
    compact_field = (
        changed_field.split(".", 1)[1]
        if changed_field.startswith("detail_price_calculation.")
        else None
    )
    if compact_field in {
        "material_price",
        "salary_fund_with_taxes",
        "price_special_equipment",
    }:
        compact["price_without_vat"] = round(sum(number(compact.get(field)) for field in (
            "material_price",
            "salary_fund_with_taxes",
            "price_special_equipment",
        )), 2)
        compact_field = "price_without_vat"
    if compact_field == "price_without_vat":
        detail_price = round(number(compact.get("price_without_vat")), 2)
        compact["taxes"] = round(detail_price * float(VAT_RATE), 2)
        compact["total"] = round(detail_price + number(compact.get("taxes")), 2)
        breakdown["detail_price"] = detail_price
        result["detail_price"] = detail_price
        result["detail_price_one"] = round(detail_price / k_quantity, 2) if k_quantity else detail_price
        result["total_price"] = round(detail_price * quantity, 2)
    elif compact_field == "taxes":
        compact["total"] = round(
            number(compact.get("price_without_vat")) + number(compact.get("taxes")),
            2,
        )

    if changed_field == "total_price_breakdown.detail_price":
        detail_price = round(number(breakdown.get("detail_price")), 2)
        result["detail_price"] = detail_price
        result["detail_price_one"] = round(detail_price / k_quantity, 2) if k_quantity else detail_price
        result["total_price"] = round(detail_price * quantity, 2)
        compact["price_without_vat"] = detail_price
        compact["taxes"] = round(detail_price * float(VAT_RATE), 2)
        compact["total"] = round(detail_price + number(compact.get("taxes")), 2)
    elif changed_field == "detail_price_one":
        detail_price_one = number(result.get("detail_price_one"))
        detail_price = round(detail_price_one * k_quantity, 2)
        result["detail_price"] = detail_price
        result["total_price"] = round(detail_price * quantity, 2)
        breakdown["detail_price"] = detail_price
        compact["price_without_vat"] = detail_price
        compact["taxes"] = round(detail_price * float(VAT_RATE), 2)
        compact["total"] = round(detail_price + number(compact.get("taxes")), 2)

    result["mat_price"] = mat_price
    result["work_price"] = work_price
    result["k_quantity"] = k_quantity
    result["total_price_breakdown"] = breakdown
    result["detail_price_calculation"] = compact
    return result


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
    material_data = lookup_material(material_id)
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