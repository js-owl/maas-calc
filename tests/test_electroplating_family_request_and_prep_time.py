from calculations.electroplating import calculate_electroplating_parameters
from utils.electroplating_config import (
    ELECTROPLATING_OPERATION_PROFILES,
    ELECTROPLATING_SERVICE_ID,
    get_material_families_for_process,
)
from utils.validation_utils import validate_calculation_request


FEATURES_SMALL = {
    "surface_area": 1_000.0,
    "volume": 1_000.0,
    "obb_x": 10.0,
    "obb_y": 10.0,
    "obb_z": 10.0,
}


def test_electroplating_calculation_accepts_family_without_material_id():
    params = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        electroplating_family="carbon_steel",
        process_id="galvanization_zinc_phosphating",
        coating_thickness_microns=9.0,
        quantity=1,
    )

    assert params["material_family"]["id"] == "carbon_steel"
    assert params["process"]["id"] == "galvanization_zinc_phosphating"
    assert params["part_weight_kg"] > 0


def test_electroplating_validation_accepts_family_without_material_id():
    errors = validate_calculation_request({
        "service_id": ELECTROPLATING_SERVICE_ID,
        "electroplating_family": "carbon_steel",
        "electroplating_process_id": "galvanization_zinc_phosphating",
        "coating_thickness_microns": 9.0,
        "quantity": 1,
        "location": "location_1",
        "file_type": "stp",
    })

    assert not [error for error in errors if error.field in {"material_id", "electroplating_family"}]


def test_electroplating_validation_rejects_wrong_family_for_process():
    errors = validate_calculation_request({
        "service_id": ELECTROPLATING_SERVICE_ID,
        "electroplating_family": "aluminum",
        "electroplating_process_id": "galvanization_zinc_phosphating",
        "coating_thickness_microns": 9.0,
        "quantity": 1,
        "location": "location_1",
        "file_type": "stp",
    })

    assert any(error.field == "electroplating_family" for error in errors)


def test_preparation_time_can_be_overridden_per_selected_process():
    operation_id = "galvanization_zinc_phosphating"
    binding = ELECTROPLATING_OPERATION_PROFILES[operation_id]
    old_value = binding.get("preparation_time_min")
    binding["preparation_time_min"] = 45.0
    try:
        params = calculate_electroplating_parameters(
            features=FEATURES_SMALL,
            electroplating_family="carbon_steel",
            process_id=operation_id,
            coating_thickness_microns=9.0,
            quantity=1,
        )
    finally:
        if old_value is None:
            binding.pop("preparation_time_min", None)
        else:
            binding["preparation_time_min"] = old_value

    assert params["preparation_time_min"] == 45.0
    assert params["operation_time_min"] == params["coating_time_min"] + 45.0


def test_material_families_for_process_selector():
    families = get_material_families_for_process("galvanization_zinc_phosphating")

    assert set(families) == {"carbon_steel"}
