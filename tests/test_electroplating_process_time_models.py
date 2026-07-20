import pytest

import calculations.electroplating as ep
from calculations.electroplating import calculate_electroplating_parameters
import utils.electroplating_config as ec
from utils.electroplating_config import ELECTROPLATING_OPERATIONS, get_process_params


@pytest.fixture(autouse=True)
def _stable_bath_layout_defaults(monkeypatch):
    """Keep process-time tests independent from bath-layout tuning constants."""
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})


FEATURES_SMALL = {
    "surface_area": 1_000.0,  # 0.1 dm²
    "volume": 1_000.0,        # 0.001 dm³
    "obb_x": 10.0,
    "obb_y": 10.0,
    "obb_z": 10.0,
}


def test_every_operation_has_explicit_process_time_model():
    processes = get_process_params()
    operation_ids = {operation["id"] for operation in ELECTROPLATING_OPERATIONS}
    assert operation_ids == set(processes)

    for process_id, process in processes.items():
        assert process.get("profile_key"), process_id
        assert process.get("time_model") in {
            "faraday_deposition",
            "faraday_layer_growth",
            "faraday_material_removal",
            "fixed_time",
        }, process_id
        assert process.get("thickness_role"), process_id


def test_all_electroplating_processes_calculate_with_their_declared_model():
    for process_id, process in get_process_params().items():
        family_id = process["material_families"][0]
        params = calculate_electroplating_parameters(
            features=FEATURES_SMALL,
            material_id=f"test_{family_id}",
            material_info={"electroplating_family": family_id},
            process_id=process_id,
            cover_id=None,
            coating_thickness_microns=None,
            processing_depth_microns=None,
            quantity=2,
        )
        assert params["time_model"] == process["time_model"]
        assert params["operation_time_min"] >= params["preparation_time_min"]
        assert params["labor_time_hours"] > 0


def test_electropolishing_uses_removal_depth_not_coating_thickness():
    params = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        material_id="test_stainless",
        material_info={"electroplating_family": "stainless_steel"},
        process_id="electropolishing",
        cover_id=None,
        coating_thickness_microns=None,
        processing_depth_microns=12.0,
        quantity=3,
    )

    assert params["time_model"] == "faraday_material_removal"
    assert params["thickness_role"] == "removed_layer_depth"
    assert params["coating_thickness_microns"] is None
    assert params["processing_depth_microns"] == 12.0
    assert params["process_parameter_name"] == "processing_depth_microns"
    assert params["process_parameter_microns"] == 12.0


def test_fixed_time_processes_do_not_depend_on_coating_thickness_by_default():
    params_default = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        material_id="test_aluminum",
        material_info={"electroplating_family": "aluminum"},
        process_id="aluminum_weld_etching",
        cover_id=None,
        coating_thickness_microns=None,
        quantity=1,
    )
    params_with_thickness = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        material_id="test_aluminum",
        material_info={"electroplating_family": "aluminum"},
        process_id="aluminum_weld_etching",
        cover_id=None,
        coating_thickness_microns=99.0,
        quantity=1,
    )

    assert params_default["time_model"] == "fixed_time"
    assert params_default["coating_thickness_microns"] is None
    assert params_default["coating_time_min"] == params_with_thickness["coating_time_min"]


def test_norm_based_fixed_operation_times_are_disabled_by_default():
    processes = get_process_params()

    for process_id, operation_time in ec.ELECTROPLATING_FIXED_OPERATION_TIME_MIN_BY_PROCESS.items():
        process = processes[process_id]
        family_id = process["material_families"][0]
        prep_time = process["preparation_time_min"]
        params_default = calculate_electroplating_parameters(
            features=FEATURES_SMALL,
            electroplating_family=family_id,
            process_id=process_id,
            coating_thickness_microns=None,
            quantity=1,
        )
        params_thick = calculate_electroplating_parameters(
            features=FEATURES_SMALL,
            electroplating_family=family_id,
            process_id=process_id,
            coating_thickness_microns=999.0,
            quantity=1,
        )

        assert params_default["time_model"] == "fixed_time", process_id
        assert params_default["preparation_time_min"] == prep_time, process_id
        assert process["configured_fixed_operation_time_min"] == operation_time, process_id
        assert process["fixed_operation_time_min"] == 0.0, process_id
        assert params_default["coating_time_min"] == 0.0, process_id
        assert params_default["operation_time_min"] == prep_time, process_id
        assert params_default["coating_time_min"] == params_thick["coating_time_min"], process_id
        assert params_default["operation_time_min"] == params_thick["operation_time_min"], process_id
        assert params_default["coating_thickness_microns"] is None, process_id
        assert params_default["uses_fixed_operation_time_by_process"] is False, process_id


def test_norm_based_fixed_operation_times_can_be_enabled(monkeypatch):
    monkeypatch.setitem(ec.ELECTROPLATING_TIME_MODEL_CONFIG, "use_fixed_operation_time_by_process", True)
    process = get_process_params()["aluminum_chemical_oxidation"]
    expected_prep_time = process["preparation_time_min"]
    expected_operation_time = process["fixed_operation_time_min"]

    params = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        electroplating_family="aluminum",
        process_id="aluminum_chemical_oxidation",
        coating_thickness_microns=None,
        quantity=1,
    )

    assert params["time_model"] == "fixed_time"
    assert params["preparation_time_min"] == expected_prep_time
    assert params["coating_time_min"] == expected_operation_time
    assert params["operation_time_min"] == expected_prep_time + expected_operation_time
    assert params["uses_fixed_operation_time_by_process"] is True


def test_coating_thickness_does_not_affect_operation_time_by_default():
    params_thin = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        electroplating_family="carbon_steel",
        process_id="galvanization_zinc_phosphating",
        coating_thickness_microns=5.0,
        quantity=1,
    )
    params_thick = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        electroplating_family="carbon_steel",
        process_id="galvanization_zinc_phosphating",
        coating_thickness_microns=50.0,
        quantity=1,
    )

    assert params_thin["time_model"] == "faraday_deposition"
    assert params_thick["time_model"] == "faraday_deposition"
    assert params_thin["coating_time_min"] == 0.0
    assert params_thick["coating_time_min"] == 0.0
    assert params_thin["operation_time_min"] == params_thick["operation_time_min"]
    assert params_thin["uses_thickness_dependent_operation_time"] is False


def test_coating_thickness_operation_time_can_be_enabled(monkeypatch):
    monkeypatch.setitem(ec.ELECTROPLATING_TIME_MODEL_CONFIG, "use_thickness_dependent_operation_time", True)

    params_thin = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        electroplating_family="carbon_steel",
        process_id="galvanization_zinc_phosphating",
        coating_thickness_microns=5.0,
        quantity=1,
    )
    params_thick = calculate_electroplating_parameters(
        features=FEATURES_SMALL,
        electroplating_family="carbon_steel",
        process_id="galvanization_zinc_phosphating",
        coating_thickness_microns=50.0,
        quantity=1,
    )

    assert params_thin["uses_thickness_dependent_operation_time"] is True
    assert params_thick["uses_thickness_dependent_operation_time"] is True
    assert params_thin["coating_time_min"] > 0
    assert params_thick["coating_time_min"] == pytest.approx(10 * params_thin["coating_time_min"])
    assert params_thick["operation_time_min"] > params_thin["operation_time_min"]


def test_requires_thickness_input_flag_matches_time_model():
    processes = get_process_params()

    assert processes["galvanization_zinc_phosphating"]["requires_thickness_input"] is False
    assert processes["chrome_plating"]["requires_thickness_input"] is False
    assert processes["aluminum_anodizing_strong"]["requires_thickness_input"] is False

    assert processes["aluminum_weld_etching"]["requires_thickness_input"] is False
    assert processes["aluminum_chemical_oxidation"]["requires_thickness_input"] is False
    assert processes["aluminum_anodizing_water"]["requires_thickness_input"] is False
    assert processes["electropolishing"]["requires_thickness_input"] is False
    assert processes["electropolishing"]["requires_processing_depth_input"] is True


def test_requires_thickness_input_flag_can_be_enabled(monkeypatch):
    monkeypatch.setitem(ec.ELECTROPLATING_TIME_MODEL_CONFIG, "use_thickness_dependent_operation_time", True)

    processes = get_process_params()

    assert processes["galvanization_zinc_phosphating"]["requires_thickness_input"] is True
    assert processes["chrome_plating"]["requires_thickness_input"] is True
    assert processes["aluminum_anodizing_strong"]["requires_thickness_input"] is True
    assert processes["electropolishing"]["requires_thickness_input"] is False
