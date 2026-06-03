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
