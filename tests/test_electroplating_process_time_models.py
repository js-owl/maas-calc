from calculations.electroplating import calculate_electroplating_parameters
from utils.electroplating_config import ELECTROPLATING_OPERATIONS, get_process_params


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
        assert params["operation_time_min"] > params["preparation_time_min"]
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


def test_fixed_time_processes_do_not_depend_on_coating_thickness():
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
