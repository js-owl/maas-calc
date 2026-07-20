import pytest

from constants import ELECTROPLATING_LABOR_TIME_COEF

import calculations.electroplating as ep


_BATCH10_PROCESS_ID = "test_batch10"
_BATCH10_BATH = {
    "length": 500.0,
    "width": 1000.0,
    "height": 50.0,
    "max_weight_kg": 1_000.0,
}
_BATCH10_DIMS_MM = (80.0, 30.0, 30.0)  # with 20 mm clearance -> ideal plane packing is 100 pcs, practical is 10 pcs


def _patch_batch10_bath(monkeypatch, process_id=_BATCH10_PROCESS_ID, *, max_weight_kg=1_000.0):
    bath = dict(_BATCH10_BATH)
    bath["max_weight_kg"] = max_weight_kg
    monkeypatch.setattr(ep, "get_baths", lambda: {process_id: bath, "default": bath})
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 20.0, "mount_unmount_time_min": 0.0})
    monkeypatch.setattr(ep, "PRACTICAL_GEOMETRIC_CAPACITY_FACTOR", 0.10)


def test_bath_layout_packs_ten_parts_and_eleventh_requires_second_batch(monkeypatch):
    _patch_batch10_bath(monkeypatch)
    process = {
        "id": _BATCH10_PROCESS_ID,
        "is_electrolytic": False,
        "max_weight_kg": 1_000.0,
    }

    layout_10 = ep.calculate_bath_layout(
        dimensions_mm=_BATCH10_DIMS_MM,
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=0.5,
        quantity=10,
    )
    layout_11 = ep.calculate_bath_layout(
        dimensions_mm=_BATCH10_DIMS_MM,
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=0.5,
        quantity=11,
    )

    assert layout_10["geometric_capacity"] == 100
    assert layout_10["practical_geometric_capacity"] == 10
    assert layout_10["batch_capacity"] == 10
    assert layout_10["batch_quantity"] == 10
    assert layout_10["batch_count"] == 1
    assert layout_10["batch_quantity_limited_by"] == "geometry"

    assert layout_11["geometric_capacity"] == 100
    assert layout_11["practical_geometric_capacity"] == 10
    assert layout_11["batch_capacity"] == 10
    assert layout_11["batch_quantity"] == 10
    assert layout_11["batch_count"] == 2
    assert layout_11["batch_quantity_limited_by"] == "geometry"


def test_bath_layout_limits_one_batch_by_total_loaded_weight(monkeypatch):
    _patch_batch10_bath(monkeypatch, max_weight_kg=10.0)
    process = {
        "id": _BATCH10_PROCESS_ID,
        "is_electrolytic": False,
        "max_weight_kg": 10.0,
    }

    layout = ep.calculate_bath_layout(
        dimensions_mm=_BATCH10_DIMS_MM,
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=2.0,
        quantity=10,
    )

    assert layout["geometric_capacity"] == 100
    assert layout["practical_geometric_capacity"] == 10
    assert layout["weight_capacity"] == 5
    assert layout["batch_capacity"] == 5
    assert layout["batch_quantity"] == 5
    assert layout["batch_quantity_limited_by"] == "weight"
    assert layout["batch_weight_kg"] == pytest.approx(10.0)
    assert layout["requested_total_weight_kg"] == pytest.approx(20.0)
    assert layout["batch_count"] == 2


def test_order_labor_is_linear_when_quantity_crosses_one_bath_capacity(monkeypatch):
    process_id = "steel_phosphating_zinc"
    _patch_batch10_bath(monkeypatch, process_id=process_id)
    features = {
        "surface_area": 10_000.0,
        "volume": 100_000.0,
        "obb_x": _BATCH10_DIMS_MM[0],
        "obb_y": _BATCH10_DIMS_MM[1],
        "obb_z": _BATCH10_DIMS_MM[2],
    }

    params_10 = ep.calculate_electroplating_parameters(
        features=features,
        electroplating_family="carbon_steel",
        process_id=process_id,
        quantity=10,
    )
    params_11 = ep.calculate_electroplating_parameters(
        features=features,
        electroplating_family="carbon_steel",
        process_id=process_id,
        quantity=11,
    )

    assert params_10["layout"]["batch_capacity"] == 10
    assert params_10["layout"]["batch_count"] == 1
    assert params_11["layout"]["batch_capacity"] == 10
    assert params_11["layout"]["batch_count"] == 2

    one_batch_process_labor = ELECTROPLATING_LABOR_TIME_COEF * params_10["operation_time_min"]
    mount_time = params_10["mount_unmount_time_min"]

    assert params_10["order_labor_time_min"] == pytest.approx(
        one_batch_process_labor + 10 * mount_time
    )
    assert params_11["order_labor_time_min"] == pytest.approx(
        1.1 * one_batch_process_labor + 11 * mount_time
    )

    # The money calculation is proportional to per-part labor time multiplied
    # by quantity. The extra 11th part adds one more per-detail labor unit, not
    # a whole extra operation cycle.
    assert params_10["labor_time_hours"] * 10 == pytest.approx(params_10["order_labor_time_hours"])
    assert params_11["labor_time_hours"] * 11 == pytest.approx(params_11["order_labor_time_hours"])

    actual_increment = params_11["order_labor_time_min"] - params_10["order_labor_time_min"]
    assert actual_increment == pytest.approx(one_batch_process_labor / 10 + mount_time)
    assert actual_increment == pytest.approx(params_10["labor_time_min"])


@pytest.mark.parametrize("batch_capacity", [1, 2, 3, 7, 10, 25])
@pytest.mark.parametrize("completed_batches", [1, 2, 5, 10])
def test_batch_count_steps_at_every_capacity_boundary(monkeypatch, batch_capacity, completed_batches):
    """Any +1 part beyond a full set of bath loads must create one more load."""
    process_id = f"capacity_{batch_capacity}"
    bath = {
        "length": float(batch_capacity * 10),
        "width": 100.0,
        "height": 10.0,
        "max_weight_kg": 1_000_000.0,
    }
    monkeypatch.setattr(ep, "get_baths", lambda: {process_id: bath, "default": bath})
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})
    monkeypatch.setattr(ep, "PRACTICAL_GEOMETRIC_CAPACITY_FACTOR", 0.10)

    process = {"id": process_id, "is_electrolytic": False, "max_weight_kg": 1_000_000.0}
    q_before = batch_capacity * completed_batches
    q_after = q_before + 1

    before = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=q_before,
    )
    after = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=q_after,
    )

    assert before["layout"]["packing_model"] == "hanging_plane"
    assert before["geometric_capacity"] == batch_capacity * 10
    assert before["practical_geometric_capacity"] == batch_capacity
    assert before["batch_capacity"] == batch_capacity
    assert before["batch_count"] == completed_batches
    assert before["batch_quantity"] == batch_capacity

    assert after["layout"]["packing_model"] == "hanging_plane"
    assert after["geometric_capacity"] == batch_capacity * 10
    assert after["practical_geometric_capacity"] == batch_capacity
    assert after["batch_capacity"] == batch_capacity
    assert after["batch_count"] == completed_batches + 1
    assert after["batch_quantity"] == batch_capacity
    assert after["batch_quantity_limited_by"] == "geometry"


@pytest.mark.parametrize("batch_capacity", [3, 10, 25])
@pytest.mark.parametrize("completed_batches", [1, 2, 5, 10])
def test_order_labor_scales_linearly_at_every_capacity_boundary(monkeypatch, batch_capacity, completed_batches):
    """Order-level labor must scale by requested quantity, not by bath_count jumps."""
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})
    operation_time_min = 60.0
    one_batch_operation_labor = ELECTROPLATING_LABOR_TIME_COEF * operation_time_min
    q_before = batch_capacity * completed_batches
    q_after = q_before + 1

    before = ep.calculate_electroplating_labor_hours(
        operation_time_min=operation_time_min,
        batch_quantity=batch_capacity,
        workers_count=1,
        requested_quantity=q_before,
        batch_count=completed_batches,
    )
    after = ep.calculate_electroplating_labor_hours(
        operation_time_min=operation_time_min,
        batch_quantity=batch_capacity,
        workers_count=1,
        requested_quantity=q_after,
        batch_count=completed_batches + 1,
    )

    assert before["order_labor_time_min"] == pytest.approx(
        completed_batches * one_batch_operation_labor
    )
    assert after["order_labor_time_min"] == pytest.approx(
        (q_after / batch_capacity) * one_batch_operation_labor
    )
    assert after["order_labor_time_min"] - before["order_labor_time_min"] == pytest.approx(
        one_batch_operation_labor / batch_capacity
    )
    assert after["labor_formula_effective_n"] == pytest.approx(batch_capacity)


@pytest.mark.parametrize("completed_batches", [1, 2, 5, 10])
def test_weight_limited_batch_count_steps_at_every_weight_boundary(monkeypatch, completed_batches):
    """The same boundary behavior is required when capacity is limited by mass."""
    process_id = "weight_step"
    bath = {
        "length": 10_000.0,
        "width": 10_000.0,
        "height": 10_000.0,
        "max_weight_kg": 30.0,
    }
    monkeypatch.setattr(ep, "get_baths", lambda: {process_id: bath, "default": bath})
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})
    monkeypatch.setattr(ep, "PRACTICAL_GEOMETRIC_CAPACITY_FACTOR", 1.0)

    process = {"id": process_id, "is_electrolytic": False, "max_weight_kg": 30.0}
    part_weight_kg = 10.0
    batch_capacity = 3
    q_before = batch_capacity * completed_batches
    q_after = q_before + 1

    before = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=part_weight_kg,
        quantity=q_before,
    )
    after = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=part_weight_kg,
        quantity=q_after,
    )

    assert before["weight_capacity"] == batch_capacity
    assert before["batch_capacity"] == batch_capacity
    assert before["batch_count"] == completed_batches
    assert before["batch_weight_kg"] == pytest.approx(30.0)

    assert after["weight_capacity"] == batch_capacity
    assert after["batch_capacity"] == batch_capacity
    assert after["batch_count"] == completed_batches + 1
    assert after["batch_quantity_limited_by"] == "weight"


@pytest.mark.parametrize("completed_batches", [1, 2, 5, 10])
def test_current_limited_batch_count_steps_at_every_current_boundary(monkeypatch, completed_batches):
    """The same boundary behavior is required when capacity is limited by current."""
    process_id = "current_step"
    bath = {
        "length": 10_000.0,
        "width": 10_000.0,
        "height": 10_000.0,
        "max_weight_kg": 1_000_000.0,
    }
    monkeypatch.setattr(ep, "get_baths", lambda: {process_id: bath, "default": bath})
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})
    monkeypatch.setattr(ep, "PRACTICAL_GEOMETRIC_CAPACITY_FACTOR", 1.0)

    process = {
        "id": process_id,
        "is_electrolytic": True,
        "max_weight_kg": 1_000_000.0,
        "current_density_a_dm2": 10.0,
        "max_current_a": 50.0,
    }
    batch_capacity = 5
    q_before = batch_capacity * completed_batches
    q_after = q_before + 1

    before = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=q_before,
    )
    after = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=q_after,
    )

    assert before["current_capacity"] == batch_capacity
    assert before["batch_capacity"] == batch_capacity
    assert before["batch_count"] == completed_batches

    assert after["current_capacity"] == batch_capacity
    assert after["batch_capacity"] == batch_capacity
    assert after["batch_count"] == completed_batches + 1
    assert after["batch_quantity_limited_by"] == "current"
