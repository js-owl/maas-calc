"""Snapshot adapter around the declarative Hamilton pricing graph."""

from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping, Set

from commercial_constants import COST_STRUCTURE
from constants import PRINTING_LOCATION
from hamilton import driver

from . import price_graph
from .core import lookup_material, resolve_priced_material_form


_DRIVER = driver.Builder().with_modules(price_graph).build()

_ALIASES = {
    "mat_price": ("mat_price", "total_price_breakdown.mat_price"),
    "work_price": ("work_price", "total_price_breakdown.work_price"),
    "total_time": ("total_time", "total_price_breakdown.total_time"),
    "is_need_special_equipment": (
        "is_need_special_equipment",
        "total_price_breakdown.is_need_special_equipment",
    ),
    "detail_price": ("detail_price", "total_price_breakdown.detail_price"),
}
_PATHS = {
    "mat_volume": ("mat_volume",),
    "mat_weight": ("mat_weight",),
    "price_of_hour": ("total_price_breakdown.price_of_hour",),
    "price_of_hour_with_others": (
        "total_price_breakdown.price_of_hour_with_others",
    ),
    "dop_salary": ("total_price_breakdown.dop_salary",),
    "insurance_price": ("total_price_breakdown.insurance_price",),
    "overhead_expenses": ("total_price_breakdown.overhead_expenses",),
    "administrative_expenses": (
        "total_price_breakdown.administrative_expenses",
    ),
    "net_cost": ("total_price_breakdown.net_cost",),
    "profit": ("total_price_breakdown.profit",),
    "cost": ("total_price_breakdown.cost",),
    "material_price_special_equipment": (
        "total_price_breakdown.material_price_special_equipment",
    ),
    "price_special_equipment": (
        "total_price_breakdown.price_special_equipment",
    ),
    "price_special_equipment_to_quantity": (
        "total_price_breakdown.price_special_equipment_to_quantity",
    ),
    "k_quantity": ("k_quantity",),
    "detail_price_one": ("detail_price_one",),
    "total_price": ("total_price",),
    "compact_material_price": ("detail_price_calculation.material_price",),
    "compact_salary_fund_with_taxes": (
        "detail_price_calculation.salary_fund_with_taxes",
    ),
    "compact_price_special_equipment": (
        "detail_price_calculation.price_special_equipment",
    ),
    "compact_price_without_vat": (
        "detail_price_calculation.price_without_vat",
    ),
    "compact_taxes": ("detail_price_calculation.taxes",),
    "compact_total": ("detail_price_calculation.total",),
}
_PATHS.update(_ALIASES)
_PATH_TO_NODE = {
    path: node for node, paths in _PATHS.items() for path in paths
}
_TRIGGER_NODES = {
    field: field
    for field in (
        "service_id",
        "material_id",
        "material_form",
        "length",
        "width",
        "height",
        "quantity",
        "k_otk",
        "cover_id",
        "finish_id",
        "tolerance_id",
    )
}
_COMPUTED_NODES = {
    node
    for node in _PATHS
    if node
    not in {
        "total_time",
        "price_of_hour",
        "is_need_special_equipment",
        "material_price_special_equipment",
    }
}
_COMPACT_NODES = {
    "compact_material_price",
    "compact_salary_fund_with_taxes",
    "compact_price_special_equipment",
    "compact_price_without_vat",
    "compact_taxes",
    "compact_total",
}
_UNIT_NODES = {
    "detail_price_one",
    "detail_price",
    "total_price",
} | _COMPACT_NODES
_LABOR_COMPONENT_NODES = {
    "dop_salary",
    "insurance_price",
    "overhead_expenses",
    "administrative_expenses",
}
_PASSTHROUGH_FIELDS = {
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


def _get(data: Mapping[str, Any], path: str, default: Any = None) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def _set(data: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        nested = current.get(part)
        if not isinstance(nested, dict):
            nested = {}
            current[part] = nested
        current = nested
    current[parts[-1]] = value


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _canonical_values(
    snapshot: Mapping[str, Any],
    changed_field: str,
) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    changed_node = _PATH_TO_NODE.get(changed_field) or _TRIGGER_NODES.get(
        changed_field
    )
    for node, paths in _PATHS.items():
        if node == changed_node:
            values[node] = _get(snapshot, changed_field)
            continue
        # Nested breakdown values are authoritative when a snapshot contains
        # stale duplicates from the top level.
        read_paths = tuple(reversed(paths)) if node in _ALIASES else paths
        for path in read_paths:
            value = _get(snapshot, path)
            if value is not None:
                values[node] = value
                break
    return values


def _inputs(
    snapshot: Mapping[str, Any],
    values: Mapping[str, Any],
) -> Dict[str, Any]:
    service_id = str(snapshot.get("service_id") or "")
    location = PRINTING_LOCATION if service_id == "printing" else "location_1"
    structure = COST_STRUCTURE.get(location) or {}
    return {
        "service_id": service_id,
        "material_id": str(snapshot.get("material_id") or ""),
        "material_form": str(snapshot.get("material_form") or ""),
        "length": _number(snapshot.get("length")),
        "width": _number(snapshot.get("width")),
        "height": _number(snapshot.get("height")),
        "quantity": max(int(snapshot.get("quantity") or 1), 1),
        "k_otk": _number(snapshot.get("k_otk"), 1.0) or 1.0,
        "cover_id": list(snapshot.get("cover_id") or []),
        "finish_id": str(snapshot.get("finish_id") or ""),
        "tolerance_id": str(snapshot.get("tolerance_id") or ""),
        "total_time": _number(values.get("total_time")),
        "price_of_hour": _number(
            values.get("price_of_hour"),
            _number(structure.get("price_of_hour")),
        ),
        "is_need_special_equipment": bool(
            values.get("is_need_special_equipment", False)
        ),
        "material_price_special_equipment": _number(
            values.get("material_price_special_equipment")
        ),
    }


def _downstream(*nodes: str) -> Set[str]:
    result: Set[str] = set()
    for node in nodes:
        downstream = _DRIVER.what_is_downstream_of(node)
        result.update(item.name for item in downstream)
    return result


def _snapshot_overrides(values: Mapping[str, Any]) -> Dict[str, Any]:
    overrides = {
        node: value
        for node, value in values.items()
        if node in _COMPUTED_NODES and value is not None
    }
    overrides["raw_price_special_equipment_to_quantity"] = _number(
        values.get("price_special_equipment_to_quantity")
    )
    return overrides


def _execute(
    inputs: Dict[str, Any],
    values: Mapping[str, Any],
    affected: Iterable[str],
    pinned: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    affected_nodes = set(affected)
    final_vars = sorted(affected_nodes & set(_PATHS))
    if not final_vars:
        return {}
    overrides = _snapshot_overrides(values)
    for node in affected_nodes:
        overrides.pop(node, None)
    overrides.update(pinned or {})
    return _DRIVER.execute(
        final_vars=final_vars,
        inputs=inputs,
        overrides=overrides,
    )


def _merge(
    snapshot: Dict[str, Any],
    values: Mapping[str, Any],
    *,
    compatibility_compact_fields: bool = False,
) -> None:
    for node, value in values.items():
        for path in _PATHS.get(node, ()):
            _set(snapshot, path, value)
    if compatibility_compact_fields and "compact_price_without_vat" in values:
        compact = snapshot["detail_price_calculation"]
        compact["detail_price_one"] = values["compact_price_without_vat"]
        compact["detail_price_one_with_taxes"] = values["compact_total"]


def _reverse_unit(
    snapshot: Dict[str, Any],
    inputs: Dict[str, Any],
    values: Dict[str, Any],
    detail_price: float,
    *,
    exact_total: float | None = None,
) -> Dict[str, Any]:
    detail_price = round(detail_price, 2)
    kq = _number(values.get("k_quantity"), 1.0)
    values["detail_price"] = detail_price
    values["detail_price_one"] = (
        round(detail_price / kq, 2) if kq else detail_price
    )
    calculated = _execute(
        inputs,
        values,
        _downstream("detail_price"),
        pinned={"detail_price": detail_price},
    )
    calculated["detail_price"] = detail_price
    calculated["detail_price_one"] = values["detail_price_one"]
    if exact_total is not None:
        calculated["total_price"] = round(exact_total, 2)
    _merge(snapshot, calculated)
    return snapshot


def recalculate_price_snapshot(
    payload: Dict[str, Any],
    changed_field: str,
) -> Dict[str, Any]:
    """Recompute only graph nodes downstream of one edited snapshot value."""
    result = deepcopy(payload)
    parts = changed_field.split(".")
    if not parts or len(parts) > 2:
        raise ValueError(f"Unsupported changed_field: {changed_field!r}")
    sentinel = object()
    source = _get(result, changed_field, sentinel)
    if source is sentinel:
        raise ValueError(f"Unknown changed_field: {changed_field!r}")
    if changed_field in _PASSTHROUGH_FIELDS:
        return result
    if source is None:
        raise ValueError(f"changed_field {changed_field!r} cannot be null")

    changed_node = _PATH_TO_NODE.get(changed_field) or _TRIGGER_NODES.get(
        changed_field
    )
    if changed_node in _ALIASES:
        for path in _ALIASES[changed_node]:
            _set(result, path, source)

    values = _canonical_values(result, changed_field)
    inputs = _inputs(result, values)
    _merge(
        result,
        {
            node: values[node]
            for node in ("mat_price", "work_price", "k_quantity")
            if node in values
        },
    )

    if changed_field == "total_price":
        total = round(_number(source), 2)
        return _reverse_unit(
            result,
            inputs,
            values,
            total / inputs["quantity"],
            exact_total=total,
        )

    if changed_node == "detail_price":
        return _reverse_unit(result, inputs, values, _number(source))

    if changed_field == "detail_price_one":
        affected = _downstream("detail_price_one")
        calculated = _execute(
            inputs,
            values,
            affected,
            pinned={"detail_price_one": _number(source)},
        )
        _merge(result, calculated)
        return result

    if changed_node in {
        "compact_material_price",
        "compact_salary_fund_with_taxes",
        "compact_price_special_equipment",
        "compact_price_without_vat",
    }:
        if changed_node == "compact_price_without_vat":
            detail = _number(source)
        else:
            detail = round(
                sum(
                    _number(values.get(node))
                    for node in (
                        "compact_material_price",
                        "compact_salary_fund_with_taxes",
                        "compact_price_special_equipment",
                    )
                ),
                2,
            )
        return _reverse_unit(result, inputs, values, detail)

    if changed_node == "compact_taxes":
        calculated = _execute(
            inputs,
            values,
            {"compact_total"},
            pinned={
                "compact_taxes": _number(source),
                "compact_price_without_vat": _number(
                    values.get("compact_price_without_vat")
                ),
            },
        )
        _merge(result, calculated)
        return result

    if changed_node == "compact_total" or changed_node is None:
        return result

    if changed_node == "price_special_equipment_to_quantity":
        unit = round(_number(source), 2)
        equipment_total = round(unit * inputs["quantity"], 2)
        values["price_special_equipment_to_quantity"] = unit
        calculated = _execute(
            inputs,
            values,
            (
                _downstream("raw_price_special_equipment_to_quantity")
                | _UNIT_NODES
            ),
            pinned={
                "raw_price_special_equipment_to_quantity": _number(source)
            },
        )
        calculated["price_special_equipment"] = equipment_total
        _merge(result, calculated, compatibility_compact_fields=True)
        return result

    if changed_node == "is_need_special_equipment":
        need_equipment = bool(source)
        inputs["is_need_special_equipment"] = need_equipment
        if not need_equipment:
            unit = 0.0
            equipment_total = 0.0
        else:
            unit = _number(values.get("price_special_equipment_to_quantity"))
            equipment_total = _number(values.get("price_special_equipment"))
        values["price_special_equipment_to_quantity"] = unit
        calculated = _execute(
            inputs,
            values,
            (
                _downstream("raw_price_special_equipment_to_quantity")
                | _UNIT_NODES
            ),
            pinned={"raw_price_special_equipment_to_quantity": unit},
        )
        calculated.update(
            {
                "price_special_equipment": round(equipment_total, 2),
                "price_special_equipment_to_quantity": round(unit, 2),
            }
        )
        _merge(result, calculated, compatibility_compact_fields=True)
        return result

    source_node = changed_node
    if changed_field in {"length", "width", "height"}:
        dimensions = ("length", "width", "height")
        if any(result.get(name) is None for name in dimensions):
            return result
        source_node = changed_field
    elif changed_field == "service_id":
        affected = {
            "dop_salary",
            "insurance_price",
            "overhead_expenses",
            "administrative_expenses",
            "net_cost",
            "profit",
            "cost",
            "detail_price_one",
            "detail_price",
            "total_price",
        } | _COMPACT_NODES
        calculated = _execute(
            inputs,
            values,
            affected,
            pinned={"work_price": _number(values.get("work_price"))},
        )
        _merge(result, calculated, compatibility_compact_fields=True)
        return result
    elif changed_field in {"material_id", "mat_volume"}:
        material_id = str(result.get("material_id") or "")
        if _number(lookup_material(material_id).get("density")) <= 0:
            source_node = "mat_price"
    elif changed_field in {"material_form", "mat_weight"}:
        material_id = str(result.get("material_id") or "")
        form_id = resolve_priced_material_form(
            material_id,
            result.get("material_form"),
            str(result.get("service_id") or ""),
        )
        form = (lookup_material(material_id).get("forms") or {}).get(
            form_id or "",
            {},
        )
        if _number(form.get("price")) <= 0:
            source_node = "mat_price"

    variables = _DRIVER.list_available_variables()
    available_nodes = {item.name for item in variables}
    if source_node not in available_nodes:
        return result

    affected = _downstream(source_node)
    rebuild_compact = changed_node not in {
        "price_of_hour_with_others",
        "compact_total",
    }
    if rebuild_compact:
        affected |= _UNIT_NODES
    if "net_cost" in affected:
        affected.update(
            node for node in _LABOR_COMPONENT_NODES if values.get(node) is None
        )

    pinned: Dict[str, Any] = {}
    if changed_node in _COMPUTED_NODES:
        pinned[changed_node] = _number(source)
    if source_node != changed_node and source_node in _COMPUTED_NODES:
        pinned[source_node] = _number(values.get(source_node))
    if changed_field == "material_id":
        pinned["mat_volume"] = _number(values.get("mat_volume"))
    elif changed_field == "material_form":
        pinned["mat_weight"] = _number(values.get("mat_weight"))
    calculated = _execute(inputs, values, affected, pinned=pinned)
    _merge(
        result,
        calculated,
        compatibility_compact_fields=rebuild_compact,
    )
    return result
