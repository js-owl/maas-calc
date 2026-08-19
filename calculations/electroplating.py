"""Rule-based calculation helpers for automatic galvanic coating pricing."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Tuple

from constants import (
    ELECTROPLATING_BATH_CLEARANCE_MM,
    ELECTROPLATING_LABOR_TIME_COEF,
    ELECTROPLATING_WEIGHT_WORKER_RULES,
    PRACTICAL_GEOMETRIC_CAPACITY_FACTOR
)
from utils.electroplating_config import (
    ELECTROPLATING_SERVICE_ID,
    NOT_APPLICABLE_ELECTROPLATING_FAMILY,
    get_baths,
    get_defaults,
    get_electroplating_process,
    get_material_families,
    get_electroplating_material_family,
    get_time_model_config,
    infer_material_family,
    normalize_electroplating_process_id,
    normalize_material_family_id,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 1) -> int:
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return default


def get_part_dimensions_mm(features: Mapping[str, Any]) -> Tuple[float, float, float]:
    """Get positive part dimensions from OBB fields or dimensions fallback."""
    candidates = (
        features.get("obb_x"),
        features.get("obb_y"),
        features.get("obb_z"),
    )
    dims = tuple(_safe_float(value) for value in candidates)
    if all(value > 0 for value in dims):
        return dims

    dimensions = features.get("dimensions")
    if isinstance(dimensions, Mapping):
        dims = (
            _safe_float(dimensions.get("length")),
            _safe_float(dimensions.get("width")),
            _safe_float(dimensions.get("height")),
        )
    else:
        dims = (
            _safe_float(getattr(dimensions, "length", None)),
            _safe_float(getattr(dimensions, "width", None)),
            _safe_float(getattr(dimensions, "height", None)),
        )

    if all(value > 0 for value in dims):
        return dims
    raise ValueError("Cannot determine positive part dimensions for electroplating bath layout")


def resolve_electroplating_process(
    process_id: Optional[str],
    cover_id: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Resolve the requested galvanic process.

    Explicit electroplating_process_id has priority. The current request shape
    also accepts the first cover_id value as the process id when
    electroplating_process_id is absent.
    """
    defaults = get_defaults()
    raw_process_id = process_id
    if not raw_process_id and cover_id:
        raw_process_id = cover_id[0]
    if not raw_process_id:
        raw_process_id = defaults.get("process_id")

    process = get_electroplating_process(raw_process_id)
    if not process:
        raise ValueError(f"Unknown electroplating process: {raw_process_id!r}")
    return process


def resolve_material_family_for_electroplating(
    electroplating_family: Optional[str] = None,
    material_id: Optional[str] = None,
    material_info: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve the material family used by electroplating_auto.

    Requests should pass electroplating_family directly because the
    electroplating price does not depend on a concrete material_id. If
    material_id is also supplied, both inputs must describe the same family.
    """
    requested_family_id = normalize_material_family_id(electroplating_family)
    fallback_family_id: Optional[str] = None

    if material_info is not None and material_id:
        fallback_family_id = infer_material_family(material_id, material_info)

    if requested_family_id == NOT_APPLICABLE_ELECTROPLATING_FAMILY:
        if fallback_family_id:
            requested_family_id = fallback_family_id
        else:
            raise ValueError(
                "electroplating_family is required for service_id='electroplating_auto'. "
                "material_id is accepted only for deriving the same family."
            )

    if fallback_family_id and fallback_family_id != requested_family_id:
        raise ValueError(
            f"electroplating_family={requested_family_id!r} does not match "
            f"for material_id {material_id!r} material_info['electroplating_family']={fallback_family_id!r}"
        )

    family = get_electroplating_material_family(requested_family_id)
    if not family:
        raise ValueError(f"Unknown or not applicable electroplating_family: {electroplating_family!r}")
    return family


def validate_process_for_material_family(process: Mapping[str, Any], material_family: Mapping[str, Any]) -> None:
    process_id = str(process.get("id", ""))
    allowed_by_family = set(material_family.get("allowed_processes") or [])
    allowed_by_process = set(process.get("material_families") or [])
    family_id = str(material_family.get("id", ""))

    if allowed_by_family and process_id not in allowed_by_family:
        raise ValueError(
            f"Process {process_id!r} is not allowed for material family {family_id!r}. "
            f"Allowed: {sorted(allowed_by_family)}"
        )
    if allowed_by_process and family_id not in allowed_by_process:
        raise ValueError(
            f"Material family {family_id!r} is not allowed for process {process_id!r}. "
            f"Allowed families: {sorted(allowed_by_process)}"
        )


def convert_geometry_to_electroplating_units(features: Mapping[str, Any]) -> Dict[str, float]:
    """Convert STP-extracted geometry from mm²/mm³ to dm²/dm³."""
    surface_area_mm2 = _safe_float(features.get("surface_area"))
    volume_mm3 = _safe_float(features.get("volume"))
    if surface_area_mm2 <= 0:
        raise ValueError("surface_area from stp_extractor.py is required and must be > 0")
    if volume_mm3 <= 0:
        raise ValueError("volume from stp_extractor.py is required and must be > 0")

    return {
        "surface_area_mm2": surface_area_mm2,
        "surface_area_dm2": surface_area_mm2 / 10_000.0,
        "volume_mm3": volume_mm3,
        "volume_dm3": volume_mm3 / 1_000_000.0,
    }


def calculate_part_weight_kg(volume_dm3: float, material_family: Mapping[str, Any]) -> float:
    density_kg_dm3 = _safe_float(material_family.get("density_kg_dm3"))
    if density_kg_dm3 <= 0:
        raise ValueError(f"Density is not configured for material family {material_family.get('id')!r}")
    return volume_dm3 * density_kg_dm3


def calculate_workers_by_weight(part_weight_kg: float) -> int:
    for max_weight_kg, workers_count in ELECTROPLATING_WEIGHT_WORKER_RULES:
        if part_weight_kg <= max_weight_kg:
            return workers_count
    max_configured_weight = ELECTROPLATING_WEIGHT_WORKER_RULES[-1][0]
    raise ValueError(
        "Electroplating worker norm is configured only for part mass up to "
        f"{max_configured_weight:g} kg"
    )


def get_hanging_plane_part_dimensions_mm(
    dimensions_mm: tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Convert raw OBB dimensions to a conservative hanging-plane model.

    Galvanic parts are usually suspended, not packed as arbitrary 3D boxes.
    For an approximate but safer automatic estimate, the two largest part
    dimensions are treated as the occupied hanging-plane projection, while the
    smallest dimension is treated as depth/thickness.
    """
    positive_dims = tuple(_safe_float(value) for value in dimensions_mm)
    if any(value <= 0 for value in positive_dims):
        raise ValueError(f"Invalid part dimensions for electroplating bath layout: {dimensions_mm!r}")

    plane_a, plane_b, depth = sorted(positive_dims, reverse=True)
    return plane_a, plane_b, depth


def part_fits_bath_dimensions_without_clearance(
    dimensions_mm: tuple[float, float, float],
    bath_dims_mm: tuple[float, float, float],
) -> bool:
    """Return whether one part can fit inside bath dimensions without clearance.

    For a single requested part we do not estimate a hanging layout. We only
    need a conservative dimension fit check. Sorting both OBB and bath
    dimensions allows the part to be oriented by its bounding box dimensions
    without tying the check to the bath's hanging-plane axes.
    """
    part_dims = sorted((_safe_float(value) for value in dimensions_mm), reverse=True)
    bath_dims = sorted((_safe_float(value) for value in bath_dims_mm), reverse=True)
    if any(value <= 0 for value in part_dims + bath_dims):
        return False
    return all(part_dim <= bath_dim for part_dim, bath_dim in zip(part_dims, bath_dims))


def calculate_current_capacity(
    *,
    process: Mapping[str, Any],
    surface_area_dm2: float,
    fallback_capacity: int,
    process_id: str,
) -> tuple[float, float, float, int]:
    """Calculate current capacity or return a neutral fallback for non-electrolytic processes."""
    current_density = _safe_float(process.get("current_density_a_dm2"))
    max_current = _safe_float(process.get("max_current_a"))
    current_per_part = current_density * surface_area_dm2 if current_density > 0 else 0.0
    if process.get("is_electrolytic", False):
        if current_per_part <= 0 or max_current <= 0:
            raise ValueError(f"Current density/max current are not configured for process {process_id!r}")
        if current_per_part > max_current:
            raise ValueError(
                f"One part requires {current_per_part:.3f} A, but bath power limit is {max_current:.3f} A"
            )
        current_capacity = max(1, int(math.floor(max_current / current_per_part)))
    else:
        current_capacity = max(1, int(fallback_capacity))

    return current_density, max_current, current_per_part, current_capacity


def build_single_part_batch_layout(
    *,
    dimensions_mm: tuple[float, float, float],
    bath_dims: tuple[float, float, float],
    baths: Mapping[str, Mapping[str, Any]],
    process: Mapping[str, Any],
    process_id: str,
    surface_area_dm2: float,
    part_weight_kg: float,
    requested_quantity: int,
    max_weight_kg: float,
    configured_clearance_mm: float,
    reason: str,
) -> Dict[str, Any]:
    """Build layout for processing one part per bath load without clearance."""
    current_density, max_current, current_per_part, current_capacity = calculate_current_capacity(
        process=process,
        surface_area_dm2=surface_area_dm2,
        fallback_capacity=1,
        process_id=process_id,
    )
    weight_capacity = max(1, int(math.floor(max_weight_kg / part_weight_kg)))
    requested_total_weight_kg = requested_quantity * part_weight_kg

    sorted_part_dims = tuple(sorted((_safe_float(value) for value in dimensions_mm), reverse=True))
    sorted_bath_dims = tuple(sorted(bath_dims, reverse=True))
    packing_model = "single_part_fit" if requested_quantity == 1 else "single_part_batches"
    layout = {
        "packing_model": packing_model,
        "working_plane_dimensions_mm": {"x": bath_dims[0], "y": bath_dims[1]},
        "orientation_mm": {"x": sorted_part_dims[0], "y": sorted_part_dims[1], "z": sorted_part_dims[2]},
        "cell_with_clearance_mm": {"x": sorted_part_dims[0], "y": sorted_part_dims[1], "z": sorted_part_dims[2]},
        "bath_dimensions_sorted_mm": {"x": sorted_bath_dims[0], "y": sorted_bath_dims[1], "z": sorted_bath_dims[2]},
        "counts": {"x": 1, "y": 1, "z": 1},
        "fits_depth": True,
        "clearance_applied": False,
        "single_part_reason": reason,
        "geometric_capacity": 1,
    }

    return {
        "bath_id": process_id if process_id in baths else "default",
        "bath_dimensions_mm": {"length": bath_dims[0], "width": bath_dims[1], "height": bath_dims[2]},
        "max_weight_kg": max_weight_kg,
        "clearance_mm": 0.0,
        "configured_clearance_mm": configured_clearance_mm,
        "layout": layout,
        "current_density_a_dm2": current_density,
        "max_current_a": max_current,
        "current_per_part_a": round(current_per_part, 6),
        "current_capacity": current_capacity,
        "geometric_capacity": 1,
        "practical_geometric_capacity": 1,
        "weight_capacity": weight_capacity,
        "requested_total_weight_kg": round(requested_total_weight_kg, 6),
        "batch_weight_kg": round(part_weight_kg, 6),
        "batch_capacity": 1,
        "batch_quantity": 1,
        "batch_quantity_limited_by": "single_part" if requested_quantity == 1 else "single_part_batches",
        "capacity_limiting_factor": "single_part" if requested_quantity == 1 else "single_part_batches",
        "capacity_limiting_factors": ["single_part" if requested_quantity == 1 else "single_part_batches"],
        "requested_quantity": requested_quantity,
        "batch_count": requested_quantity,
        "is_single_batch": requested_quantity == 1,
    }


def calculate_bath_layout(
    dimensions_mm: tuple[float, float, float],
    process: Mapping[str, Any],
    surface_area_dm2: float,
    part_weight_kg: float,
    quantity: int,
) -> Dict[str, Any]:
    """Estimate bath fit and the maximum one-bath load.

    The model is intentionally simple and deterministic: the part is represented
    by its OBB and treated as a suspended item, not as a freely rotated 3D box.
    The two largest part dimensions are used as the occupied hanging-plane
    projection. The smallest part dimension is used as the depth/thickness check.
    The working plane is defined by the first two bath dimensions. The third bath
    dimension is used only as a depth fit check, not as another packing axis.

    The final one-bath capacity is then limited by:

    - practical geometric capacity on the hanging plane;
    - maximum current for electrolytic operations;
    - maximum allowed total batch weight from ELECTROPLATING_OPERATIONS[*].max_weight_kg.
    """
    defaults = get_defaults()
    process_id = str(process.get("id") or normalize_electroplating_process_id(process.get("label")) or "default")
    baths = get_baths()
    bath = baths.get(process_id) or baths.get("default")
    if not bath:
        raise ValueError("electroplating_config.get_baths() must contain process bath or 'default' bath")

    bath_dims = (
        _safe_float(bath.get("length")),
        _safe_float(bath.get("width")),
        _safe_float(bath.get("height")),
    )
    max_weight_kg = _safe_float(process.get("max_weight_kg"), _safe_float(bath.get("max_weight_kg")))
    if any(value <= 0 for value in bath_dims):
        raise ValueError(f"Invalid bath dimensions for process {process_id!r}: {bath}")
    if max_weight_kg <= 0:
        raise ValueError(f"max_weight_kg is not configured for process {process_id!r}")

    requested_quantity = _safe_int(quantity)
    if part_weight_kg <= 0:
        raise ValueError("part_weight_kg must be > 0 for electroplating batch weight check")
    if part_weight_kg > max_weight_kg:
        raise ValueError(
            f"One part weighs {part_weight_kg:.3f} kg, but bath max_weight_kg is {max_weight_kg:.3f} kg "
            f"for process {process_id!r}"
        )

    clearance = _safe_float(defaults.get("clearance_mm"), ELECTROPLATING_BATH_CLEARANCE_MM)

    plane_dims = bath_dims[:2]
    depth_limit = bath_dims[2]
    part_plane_a, part_plane_b, part_depth = get_hanging_plane_part_dimensions_mm(dimensions_mm)
    best = None
    # Only rotate the already selected hanging-plane projection by 90 degrees.
    # Do not put the smallest dimension on the plane, because that recreates an
    # optimistic 3D-box packing estimate instead of a suspended-load estimate.
    for orientation in (
        (part_plane_a, part_plane_b, part_depth),
        (part_plane_b, part_plane_a, part_depth),
    ):
        cell = tuple(value + clearance for value in orientation)
        fits_depth = cell[2] <= depth_limit
        if fits_depth:
            plane_counts = tuple(
                int(math.floor(plane_dim / cell_dim))
                for plane_dim, cell_dim in zip(plane_dims, cell[:2])
            )
            capacity = plane_counts[0] * plane_counts[1]
        else:
            plane_counts = (0, 0)
            capacity = 0
        item = {
            "packing_model": "hanging_plane",
            "working_plane_dimensions_mm": {"x": plane_dims[0], "y": plane_dims[1]},
            "orientation_mm": {"x": orientation[0], "y": orientation[1], "z": orientation[2]},
            "cell_with_clearance_mm": {"x": cell[0], "y": cell[1], "z": cell[2]},
            "counts": {"x": plane_counts[0], "y": plane_counts[1], "z": 1 if fits_depth else 0},
            "fits_depth": fits_depth,
            "geometric_capacity": capacity,
        }
        if best is None or capacity > best["geometric_capacity"]:
            best = item

    if not best or best["geometric_capacity"] < 1:
        if part_fits_bath_dimensions_without_clearance(dimensions_mm, bath_dims):
            return build_single_part_batch_layout(
                dimensions_mm=dimensions_mm,
                bath_dims=bath_dims,
                baths=baths,
                process=process,
                process_id=process_id,
                surface_area_dm2=surface_area_dm2,
                part_weight_kg=part_weight_kg,
                requested_quantity=requested_quantity,
                max_weight_kg=max_weight_kg,
                configured_clearance_mm=clearance,
                reason=(
                    "quantity_is_one_and_hanging_plane_with_clearance_has_zero_capacity"
                    if requested_quantity == 1
                    else "hanging_plane_with_clearance_has_zero_capacity"
                ),
            )
        raise ValueError(
            f"Part does not fit in electroplating bath for process {process_id!r}. "
            f"Part OBB: {dimensions_mm}, bath: {bath_dims}, clearance: {clearance} mm"
        )

    current_density, max_current, current_per_part, current_capacity = calculate_current_capacity(
        process=process,
        surface_area_dm2=surface_area_dm2,
        fallback_capacity=best["geometric_capacity"],
        process_id=process_id,
    )

    geometric_capacity = int(best["geometric_capacity"])
    practical_geometric_capacity = max(
        1,
        int(math.floor(geometric_capacity * PRACTICAL_GEOMETRIC_CAPACITY_FACTOR)),
    )
    weight_capacity = max(1, int(math.floor(max_weight_kg / part_weight_kg)))
    batch_capacity = max(1, min(practical_geometric_capacity, current_capacity, weight_capacity))
    # This is the n used in the labor formula: (operation_coef*x)/n + z*k.
    # It is the maximum number of such parts that can be processed in one bath,
    # not the requested order quantity.
    batch_quantity = batch_capacity
    batch_count = int(math.ceil(requested_quantity / batch_capacity))
    requested_total_weight_kg = requested_quantity * part_weight_kg
    batch_weight_kg = batch_quantity * part_weight_kg

    # Only active constraints should be reported as limiting factors.
    # For non-electrolytic processes current_capacity is set to the ideal
    # geometric capacity as a neutral high value, but current is not a real limit.
    capacity_candidates = {
        "geometry": practical_geometric_capacity,
        "weight": weight_capacity,
    }
    if process.get("is_electrolytic", False):
        capacity_candidates["current"] = current_capacity
    capacity_limiting_factors = [
        factor for factor, capacity in capacity_candidates.items() if capacity == batch_capacity
    ]
    capacity_limiting_factor = "_and_".join(capacity_limiting_factors)

    return {
        "bath_id": process_id if process_id in baths else "default",
        "bath_dimensions_mm": {"length": bath_dims[0], "width": bath_dims[1], "height": bath_dims[2]},
        "max_weight_kg": max_weight_kg,
        "clearance_mm": clearance,
        "layout": best,
        "current_density_a_dm2": current_density,
        "max_current_a": max_current,
        "current_per_part_a": round(current_per_part, 6),
        "current_capacity": current_capacity,
        "geometric_capacity": geometric_capacity,
        "practical_geometric_capacity": practical_geometric_capacity,
        "weight_capacity": weight_capacity,
        "requested_total_weight_kg": round(requested_total_weight_kg, 6),
        "batch_weight_kg": round(batch_weight_kg, 6),
        "batch_capacity": batch_capacity,
        "batch_quantity": batch_quantity,
        "batch_quantity_limited_by": capacity_limiting_factor,
        "capacity_limiting_factor": capacity_limiting_factor,
        "capacity_limiting_factors": capacity_limiting_factors,
        "requested_quantity": requested_quantity,
        "batch_count": batch_count,
        "is_single_batch": batch_count == 1,
    }


def calculate_process_time_minutes(
    process: Mapping[str, Any],
    coating_thickness_microns: Optional[float],
    processing_depth_microns: Optional[float],
    material_family: Mapping[str, Any],
) -> Dict[str, Any]:
    """Calculate the operation time component for the selected galvanic process.

    There are three supported time models:

    - faraday_deposition / faraday_layer_growth: uses the configured
      T=(a*b)/(c*d*e) formula, where ``a`` is coating or oxide layer
      thickness in microns.
    - faraday_material_removal: used for electropolishing. It uses the same
      Faraday-style formula, but ``a`` is removed layer depth, not coating
      thickness.
    - fixed_time: chemical/preparatory processes. No current-density formula
      is used; fixed_operation_time_min is the configured operation duration.
    """
    time_model = str(
        process.get("time_model")
        or ("faraday_deposition" if process.get("is_electrolytic", False) else "fixed_time")
    )
    thickness_role = str(process.get("thickness_role") or "coating_thickness")
    time_model_config = get_time_model_config()

    if time_model == "fixed_time":
        fixed_time = _safe_float(
            process.get("fixed_operation_time_min"),
            _safe_float(process.get("base_operation_time_min"), 0.0),
        )
        if fixed_time < 0:
            raise ValueError(f"fixed_operation_time_min must be >= 0 for process {process.get('id')!r}")
        reference_thickness = _safe_float(process.get("default_thickness_microns"), 0.0)
        return {
            "time_model": time_model,
            "thickness_role": thickness_role,
            "coating_thickness_microns": None,
            "processing_depth_microns": None,
            "process_parameter_microns": reference_thickness if reference_thickness > 0 else None,
            "process_parameter_name": "reference_thickness_microns" if reference_thickness > 0 else None,
            "coating_time_min": fixed_time,
            "operation_time_component_min": fixed_time,
            "uses_fixed_operation_time_by_process": time_model_config["use_fixed_operation_time_by_process"],
            "uses_thickness_dependent_operation_time": False,
        }

    current_density = _safe_float(process.get("current_density_a_dm2"))
    electrochemical_equivalent = _safe_float(process.get("electrochemical_equivalent"))
    current_efficiency = _safe_float(process.get("current_efficiency"))

    if time_model == "faraday_material_removal":
        depth = _safe_float(processing_depth_microns, -1.0)
        if depth < 0:
            # Compatibility: some callers still pass material-removal depth through coating_thickness_microns.
            depth = _safe_float(coating_thickness_microns, -1.0)
        if depth < 0:
            depth = _safe_float(process.get("default_processing_depth_microns"), 0.0)

        density = _safe_float(
            process.get("removed_material_density_kg_dm3"),
            _safe_float(material_family.get("density_kg_dm3"), 0.0),
        )
        if depth <= 0:
            raise ValueError("processing_depth_microns must be > 0 for material-removal electroplating process")
        if min(density, current_density, electrochemical_equivalent, current_efficiency) <= 0:
            raise ValueError(f"Process coefficients are incomplete for process {process.get('id')!r}")

        process_time_min = (depth * density) / (
            current_density * electrochemical_equivalent * current_efficiency
        )
        return {
            "time_model": time_model,
            "thickness_role": thickness_role,
            "coating_thickness_microns": None,
            "processing_depth_microns": depth,
            "process_parameter_microns": depth,
            "process_parameter_name": "processing_depth_microns",
            "coating_time_min": process_time_min,
            "operation_time_component_min": process_time_min,
            "uses_fixed_operation_time_by_process": False,
            "uses_thickness_dependent_operation_time": False,
        }

    # Default electrolytic coating / oxide growth branch.
    thickness = _safe_float(coating_thickness_microns, -1.0)
    if thickness < 0:
        thickness = _safe_float(process.get("default_thickness_microns"), 0.0)

    if not time_model_config["use_thickness_dependent_operation_time"]:
        return {
            "time_model": time_model,
            "thickness_role": thickness_role,
            "coating_thickness_microns": thickness if thickness > 0 else None,
            "processing_depth_microns": None,
            "process_parameter_microns": thickness if thickness > 0 else None,
            "process_parameter_name": "coating_thickness_microns" if thickness > 0 else None,
            "coating_time_min": 0.0,
            "operation_time_component_min": 0.0,
            "uses_fixed_operation_time_by_process": False,
            "uses_thickness_dependent_operation_time": False,
        }

    density = _safe_float(process.get("deposited_density_kg_dm3"))
    if thickness <= 0:
        raise ValueError("coating_thickness_microns must be > 0 for coating/layer-growth process")
    if min(density, current_density, electrochemical_equivalent, current_efficiency) <= 0:
        raise ValueError(f"Process coefficients are incomplete for process {process.get('id')!r}")

    process_time_min = (thickness * density) / (
        current_density * electrochemical_equivalent * current_efficiency
    )
    return {
        "time_model": time_model,
        "thickness_role": thickness_role,
        "coating_thickness_microns": thickness,
        "processing_depth_microns": None,
        "process_parameter_microns": thickness,
        "process_parameter_name": "coating_thickness_microns",
        "coating_time_min": process_time_min,
        "operation_time_component_min": process_time_min,
        "uses_fixed_operation_time_by_process": False,
        "uses_thickness_dependent_operation_time": True,
    }


def calculate_electroplating_labor_hours(
    operation_time_min: float,
    batch_quantity: int,
    workers_count: int,
    requested_quantity: Optional[int] = None,
    batch_count: Optional[int] = None,
) -> Dict[str, float]:
    """Calculate labor for one detail and for the requested order.

    The per-detail formula is ``(operation_coef * x) / n + z * k``.
    Here ``n`` is the maximum number of such parts that fit in one bath, as
    returned by ``calculate_bath_layout``. The requested quantity does not replace
    ``n``; it only multiplies the resulting per-detail labor.
    """
    defaults = get_defaults()
    mount_time_min = _safe_float(defaults.get("mount_unmount_time_min"), 2.5)
    batch_quantity = _safe_int(batch_quantity)
    requested_quantity = _safe_int(requested_quantity, batch_quantity)
    batch_count = _safe_int(batch_count, 1)

    per_detail_operation_labor_min = ELECTROPLATING_LABOR_TIME_COEF * operation_time_min / batch_quantity
    operation_labor_total_min = per_detail_operation_labor_min * requested_quantity
    mount_unmount_total_min = workers_count * mount_time_min * requested_quantity
    labor_min = per_detail_operation_labor_min + workers_count * mount_time_min
    order_labor_time_min = operation_labor_total_min + mount_unmount_total_min
    return {
        "mount_unmount_time_min": mount_time_min,
        "labor_formula_batch_quantity_n": float(batch_quantity),
        "labor_formula_requested_quantity": float(requested_quantity),
        "labor_formula_batch_count": float(batch_count),
        "labor_formula_effective_n": float(batch_quantity),
        "per_detail_operation_labor_min": per_detail_operation_labor_min,
        "operation_labor_total_min": operation_labor_total_min,
        "mount_unmount_total_min": mount_unmount_total_min,
        "order_labor_time_min": order_labor_time_min,
        "order_labor_time_hours": order_labor_time_min / 60.0,
        "labor_time_min": labor_min,
        "labor_time_hours": labor_min / 60.0,
    }


def calculate_electroplating_parameters(
    *,
    features: Mapping[str, Any],
    material_id: Optional[str] = None,
    material_info: Optional[Mapping[str, Any]] = None,
    electroplating_family: Optional[str] = None,
    process_id: Optional[str] = None,
    cover_id: Optional[list[str]] = None,
    coating_thickness_microns: Optional[float] = None,
    quantity: int = 1,
    processing_depth_microns: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate geometry/process/labor parameters before money conversion."""
    process = resolve_electroplating_process(process_id, cover_id)
    material_family = resolve_material_family_for_electroplating(
        electroplating_family=electroplating_family,
        material_id=material_id,
        material_info=material_info,
    )
    validate_process_for_material_family(process, material_family)

    geometry = convert_geometry_to_electroplating_units(features)
    dimensions_mm = get_part_dimensions_mm(features)
    part_weight_kg = calculate_part_weight_kg(geometry["volume_dm3"], material_family)
    workers_count = calculate_workers_by_weight(part_weight_kg)
    layout = calculate_bath_layout(
        dimensions_mm=dimensions_mm,
        process=process,
        surface_area_dm2=geometry["surface_area_dm2"],
        part_weight_kg=part_weight_kg,
        quantity=quantity,
    )
    coating_time = calculate_process_time_minutes(
        process=process,
        coating_thickness_microns=coating_thickness_microns,
        processing_depth_microns=processing_depth_microns,
        material_family=material_family,
    )
    defaults = get_defaults()
    preparation_time_min = _safe_float(
        process.get("preparation_time_min"),
        _safe_float(defaults.get("preparation_time_min"), 30.0),
    )
    if preparation_time_min < 0:
        raise ValueError(f"preparation_time_min must be >= 0 for process {process.get('id')!r}")
    operation_time_min = coating_time["coating_time_min"] + preparation_time_min
    labor = calculate_electroplating_labor_hours(
        operation_time_min=operation_time_min,
        batch_quantity=layout["batch_quantity"],
        workers_count=workers_count,
        requested_quantity=layout["requested_quantity"],
        batch_count=layout["batch_count"],
    )

    return {
        "service_id": ELECTROPLATING_SERVICE_ID,
        "process": process,
        "material_family": material_family,
        "geometry": geometry,
        "dimensions_mm": {"x": dimensions_mm[0], "y": dimensions_mm[1], "z": dimensions_mm[2]},
        "part_weight_kg": part_weight_kg,
        "workers_count": workers_count,
        "layout": layout,
        "preparation_time_min": preparation_time_min,
        "operation_time_min": operation_time_min,
        "batch_quantity": layout["batch_quantity"],
        **coating_time,
        **labor,
    }
