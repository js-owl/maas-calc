import pytest

from calculations.electroplating import calculate_electroplating_parameters
from utils.electroplating_config import get_electroplating_process, get_process_params


def _features():
    return {
        "surface_area": 60_000.0,  # 6 dm²
        "volume": 100_000.0,       # 0.1 dm³ -> 0.78 kg for steel
        "obb_x": 100.0,
        "obb_y": 100.0,
        "obb_z": 100.0,
    }


def _material_info():
    return {"electroplating_family": "carbon_steel"}


def test_electroplating_config_uses_non_auto_services_operations():
    processes = get_process_params()

    assert "galvanization_zinc_phosphating" in processes
    assert "chrome_plating" in processes
    assert processes["galvanization_zinc_phosphating"]["max_part_size_mm"] == (2800.0, 700.0, 1000.0)
    assert processes["galvanization_zinc_phosphating"]["max_weight_kg"] == 400.0
    assert get_electroplating_process("zinc")["id"] == "galvanization_zinc_phosphating"


def test_electroplating_uses_requested_quantity_when_order_is_smaller_than_bath_capacity():
    params = calculate_electroplating_parameters(
        features=_features(),
        material_id="steel_test",
        material_info=_material_info(),
        process_id="zinc",
        cover_id=None,
        coating_thickness_microns=9.0,
        quantity=10,
    )

    layout = params["layout"]
    assert layout["requested_quantity"] == 10
    assert layout["batch_capacity"] >= 10
    assert layout["batch_quantity"] == 10
    assert layout["batch_quantity_limited_by"] == "requested_quantity"
    assert params["labor_formula_batch_quantity_n"] == 10.0


def test_electroplating_caps_formula_n_by_one_bath_capacity():
    params = calculate_electroplating_parameters(
        features=_features(),
        material_id="steel_test",
        material_info=_material_info(),
        process_id="zinc",
        cover_id=None,
        coating_thickness_microns=9.0,
        quantity=200,
    )

    layout = params["layout"]
    assert layout["requested_quantity"] == 200
    assert layout["current_capacity"] == 100
    assert layout["weight_capacity"] > layout["current_capacity"]
    assert layout["batch_capacity"] == 100
    assert layout["batch_quantity"] == 100
    assert layout["batch_quantity_limited_by"] == "current"
    assert layout["batch_count"] == 2
    assert params["labor_formula_batch_quantity_n"] == 100.0


def test_electroplating_caps_formula_n_by_bath_max_weight():
    features = {
        "surface_area": 10_000.0,  # 1 dm² -> chrome current capacity 50
        "volume": 256_410.2564,    # ~0.256 dm³ -> ~2 kg for steel
        "obb_x": 50.0,
        "obb_y": 50.0,
        "obb_z": 50.0,
    }

    params = calculate_electroplating_parameters(
        features=features,
        material_id="steel_test",
        material_info=_material_info(),
        process_id="chrome_plating",
        cover_id=None,
        coating_thickness_microns=9.0,
        quantity=20,
    )

    layout = params["layout"]
    assert layout["max_weight_kg"] == 10.0
    assert layout["weight_capacity"] == 5
    assert layout["current_capacity"] == 50
    assert layout["batch_capacity"] == 5
    assert layout["batch_quantity"] == 5
    assert layout["batch_quantity_limited_by"] == "weight"
    assert layout["batch_weight_kg"] == pytest.approx(10.0, abs=0.01)
    assert layout["batch_count"] == 4


def test_bath_layout_geometric_capacity_tries_orientations_and_returns_exact_capacity(monkeypatch):
    """A synthetic bath/part pair with clearance=0 should fit exactly 10 parts."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"layout_test": {"length": 100.0, "width": 100.0, "height": 10.0, "max_weight_kg": 1_000.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(50.0, 20.0, 10.0),
        process={"id": "layout_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=10,
    )

    assert layout["geometric_capacity"] == 10
    assert layout["batch_capacity"] == 10
    assert layout["batch_quantity"] == 10
    assert layout["batch_count"] == 1
    assert layout["batch_quantity_limited_by"] == "requested_quantity"
    assert layout["layout"]["counts"] in (
        {"x": 2, "y": 5, "z": 1},
        {"x": 5, "y": 2, "z": 1},
    )


def test_bath_layout_weight_limit_uses_total_weight_of_parts_in_one_bath(monkeypatch):
    """Weight capacity must be floor(max_weight_kg / part_weight_kg)."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"weight_test": {"length": 1000.0, "width": 1000.0, "height": 1000.0, "max_weight_kg": 10.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process={"id": "weight_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=2.1,
        quantity=20,
    )

    assert layout["geometric_capacity"] > 20
    assert layout["weight_capacity"] == 4
    assert layout["batch_capacity"] == 4
    assert layout["batch_quantity"] == 4
    assert layout["batch_weight_kg"] == pytest.approx(8.4)
    assert layout["batch_quantity_limited_by"] == "weight"
    assert layout["batch_count"] == 5


def test_order_labor_has_step_jump_when_new_bath_load_is_needed(monkeypatch):
    """10 parts fit in one bath; the 11th starts the second operation cycle."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"jump_test": {"length": 100.0, "width": 100.0, "height": 10.0, "max_weight_kg": 1_000.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    process = {"id": "jump_test", "is_electrolytic": False}
    layout_10 = ep.calculate_bath_layout(
        dimensions_mm=(50.0, 20.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=10,
    )
    layout_11 = ep.calculate_bath_layout(
        dimensions_mm=(50.0, 20.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=11,
    )

    assert layout_10["batch_capacity"] == 10
    assert layout_10["batch_count"] == 1
    assert layout_11["batch_capacity"] == 10
    assert layout_11["batch_count"] == 2

    labor_10 = ep.calculate_electroplating_labor_hours(
        operation_time_min=60.0,
        batch_quantity=layout_10["batch_quantity"],
        workers_count=1,
        requested_quantity=layout_10["requested_quantity"],
        batch_count=layout_10["batch_count"],
    )
    labor_11 = ep.calculate_electroplating_labor_hours(
        operation_time_min=60.0,
        batch_quantity=layout_11["batch_quantity"],
        workers_count=1,
        requested_quantity=layout_11["requested_quantity"],
        batch_count=layout_11["batch_count"],
    )

    order_labor_10 = labor_10["labor_time_min"] * 10
    order_labor_11 = labor_11["labor_time_min"] * 11

    assert labor_10["labor_formula_effective_n"] == pytest.approx(10.0)
    assert labor_11["labor_formula_effective_n"] == pytest.approx(5.5)
    assert order_labor_10 == pytest.approx(1.18 * 60.0)
    assert order_labor_11 == pytest.approx(2 * 1.18 * 60.0)
    assert order_labor_11 / order_labor_10 == pytest.approx(2.0)
