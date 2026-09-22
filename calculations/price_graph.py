"""Declarative price dependency graph for ``POST /recalculate-price``."""

from typing import Any, Dict, List

from commercial_constants import COST_STRUCTURE
from constants import COVER, FINISH, PRINTING_LOCATION, TOLERANCE, VAT_RATE

from .core import (
    calculate_cost,
    calculate_k_quantity,
    calculate_mat_price,
    calculate_mat_volume,
    calculate_mat_weight,
    lookup_material,
    resolve_priced_material_form,
)


def location(service_id: str) -> str:
    return PRINTING_LOCATION if service_id == "printing" else "location_1"


def cost_structure(location: str) -> Dict[str, Any]:
    value = COST_STRUCTURE.get(location)
    if not value:
        raise ValueError(f"Cost structure is not configured for {location!r}")
    return value


def mat_density(material_id: str) -> float:
    return float(lookup_material(material_id).get("density") or 0.0)


def mat_volume(length: float, width: float, height: float) -> float:
    return calculate_mat_volume(length, width, height)


def mat_weight(mat_volume: float, mat_density: float) -> float:
    return calculate_mat_weight(mat_volume, mat_density)


def material_unit_price(
    material_id: str,
    material_form: str,
    service_id: str,
) -> float:
    resolved_form = resolve_priced_material_form(
        material_id,
        material_form,
        service_id,
    )
    forms = lookup_material(material_id).get("forms") or {}
    return float((forms.get(resolved_form or "") or {}).get("price") or 0.0)


def mat_price(mat_weight: float, material_unit_price: float) -> float:
    return calculate_mat_price(mat_weight, material_unit_price)


def work_coefficient(
    k_otk: float,
    cover_id: List[str],
    service_id: str,
    tolerance_id: str,
    finish_id: str,
) -> float:
    coefficient = float(k_otk or 1.0)
    covers = set(cover_id or [])
    if all(cover in COVER for cover in covers):
        for cover in covers:
            coefficient *= float(COVER[cover]["value"])
    if service_id == "cnc-milling":
        coefficient *= float(
            TOLERANCE.get(str(tolerance_id), {}).get("value") or 1.0
        )
        coefficient *= float(
            FINISH.get(str(finish_id), {}).get("value") or 1.0
        )
    return coefficient


def work_price(
    total_time: float,
    price_of_hour: float,
    work_coefficient: float,
) -> float:
    return (
        float(total_time or 0.0)
        * float(price_of_hour or 0.0)
        * work_coefficient
    )


def price_of_hour_with_others(
    price_of_hour: float,
    cost_structure: Dict[str, Any],
) -> float:
    dop = float(cost_structure.get("dop_salary_coef") or 0.0)
    insurance = float(cost_structure.get("insurance_coef") or 0.0)
    multiplier = (
        1.0
        + dop
        + dop * insurance
        + insurance
        + float(cost_structure.get("overhead_expenses_coef") or 0.0)
        + float(cost_structure.get("administrative_expenses_coef") or 0.0)
    )
    return round(float(price_of_hour or 0.0) * multiplier, 2)


def dop_salary(work_price: float, cost_structure: Dict[str, Any]) -> float:
    return float(cost_structure.get("dop_salary_coef") or 0.0) * work_price


def insurance_price(
    work_price: float,
    dop_salary: float,
    cost_structure: Dict[str, Any],
) -> float:
    return float(cost_structure.get("insurance_coef") or 0.0) * (
        work_price + dop_salary
    )


def overhead_expenses(
    work_price: float,
    cost_structure: Dict[str, Any],
) -> float:
    coefficient = float(cost_structure.get("overhead_expenses_coef") or 0.0)
    return coefficient * work_price


def administrative_expenses(
    work_price: float,
    cost_structure: Dict[str, Any],
) -> float:
    coefficient = float(
        cost_structure.get("administrative_expenses_coef") or 0.0
    )
    return coefficient * work_price


def net_cost(
    mat_price: float,
    work_price: float,
    dop_salary: float,
    insurance_price: float,
    overhead_expenses: float,
    administrative_expenses: float,
) -> float:
    return sum(
        (
            mat_price,
            work_price,
            dop_salary,
            insurance_price,
            overhead_expenses,
            administrative_expenses,
        )
    )


def profit(
    mat_price: float,
    net_cost: float,
    cost_structure: Dict[str, Any],
) -> float:
    return (
        mat_price * float(cost_structure.get("profit_material") or 0.0)
        + (net_cost - mat_price)
        * float(cost_structure.get("other_profit") or 0.0)
    )


def cost(net_cost: float, profit: float) -> float:
    return round(net_cost + profit, 2)


def price_special_equipment(
    material_price_special_equipment: float,
    is_need_special_equipment: bool,
    location: str,
) -> float:
    if not is_need_special_equipment:
        return 0.0
    return float(
        calculate_cost(
            float(material_price_special_equipment or 0.0),
            0.0,
            location,
        )
    )


def raw_price_special_equipment_to_quantity(
    price_special_equipment: float,
    quantity: int,
) -> float:
    return float(price_special_equipment or 0.0) / max(int(quantity), 1)


def price_special_equipment_to_quantity(
    raw_price_special_equipment_to_quantity: float,
) -> float:
    return round(raw_price_special_equipment_to_quantity, 2)


def k_quantity(quantity: int) -> float:
    return calculate_k_quantity(quantity)


def detail_price_one(
    cost: float,
    raw_price_special_equipment_to_quantity: float,
) -> float:
    return round(cost + raw_price_special_equipment_to_quantity, 2)


def detail_price(detail_price_one: float, k_quantity: float) -> float:
    return round(detail_price_one * k_quantity, 2)


def total_price(detail_price: float, quantity: int) -> float:
    return round(detail_price * max(int(quantity), 1), 2)


def compact_material_price(
    mat_price: float,
    k_quantity: float,
    cost_structure: Dict[str, Any],
) -> float:
    return round(
        mat_price
        * (1.0 + float(cost_structure.get("profit_material") or 0.0))
        * k_quantity,
        2,
    )


def compact_salary_fund_with_taxes(
    net_cost: float,
    mat_price: float,
    k_quantity: float,
    cost_structure: Dict[str, Any],
) -> float:
    return round(
        (net_cost - mat_price)
        * (1.0 + float(cost_structure.get("other_profit") or 0.0))
        * k_quantity,
        2,
    )


def compact_price_special_equipment(
    raw_price_special_equipment_to_quantity: float,
    k_quantity: float,
) -> float:
    return round(raw_price_special_equipment_to_quantity * k_quantity, 2)


def compact_price_without_vat(detail_price: float) -> float:
    return round(detail_price, 2)


def compact_taxes(compact_price_without_vat: float) -> float:
    return round(compact_price_without_vat * float(VAT_RATE), 2)


def compact_total(
    compact_price_without_vat: float,
    compact_taxes: float,
) -> float:
    return round(compact_price_without_vat + compact_taxes, 2)
