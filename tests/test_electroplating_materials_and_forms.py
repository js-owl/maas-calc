import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constants import MATERIALS, NON_AUTO_SERVICES
from utils.electroplating_config import (
    ELECTROPLATING_OPERATIONS,
    ELECTROPLATING_SERVICE_ID,
    NOT_APPLICABLE_ELECTROPLATING_FAMILY,
    get_process_params,
    infer_material_family,
    is_material_allowed_for_electroplating,
)
from utils.validation_utils import validate_calculation_request


def test_material_families_are_explicit_and_composites_are_not_applicable():
    assert infer_material_family("steel_30XGSA", MATERIALS["steel_30XGSA"]) == "carbon_steel"
    assert infer_material_family("steel_14X17H2", MATERIALS["steel_14X17H2"]) == "stainless_steel"
    assert infer_material_family("alum_D16", MATERIALS["alum_D16"]) == "aluminum"
    assert infer_material_family("latun_Л63", MATERIALS["latun_Л63"]) == "copper"
    assert infer_material_family("t-10-14", MATERIALS["t-10-14"]) == NOT_APPLICABLE_ELECTROPLATING_FAMILY
    assert not is_material_allowed_for_electroplating("t-10-14", MATERIALS["t-10-14"])


def test_invalid_material_form_is_rejected_for_composite():
    request_data = {
        "service_id": "composite",
        "material_id": "t-10-14",
        "material_form": "rod",
        "quantity": 1,
        "file_type": "step",
    }
    errors = validate_calculation_request(request_data)
    assert any(error.field == "material_form" for error in errors)


def test_non_galvanic_material_is_rejected_for_electroplating_auto():
    request_data = {
        "service_id": ELECTROPLATING_SERVICE_ID,
        "material_id": "t-10-14",
        "material_form": "textile",
        "quantity": 1,
        "file_type": "step",
        "electroplating_process_id": "galvanization_zinc_phosphating",
    }
    errors = validate_calculation_request(request_data)
    assert any(error.field == "material_id" for error in errors)


def test_galvanic_material_and_real_form_are_accepted():
    request_data = {
        "service_id": ELECTROPLATING_SERVICE_ID,
        "material_id": "steel_30XGSA",
        "material_form": "rod",
        "quantity": 1,
        "file_type": "step",
        "electroplating_process_id": "galvanization_zinc_phosphating",
    }
    assert validate_calculation_request(request_data) == []



def test_aluminum_available_processes_do_not_include_titanium_operations():
    aluminum_processes = {
        process_id
        for process_id, process in get_process_params().items()
        if "aluminum" in process.get("material_families", [])
    }
    assert aluminum_processes
    assert all(not process_id.startswith("titanium_") for process_id in aluminum_processes)
    assert "titanium_passivation" not in aluminum_processes


def test_titanium_process_is_rejected_for_aluminum_material():
    request_data = {
        "service_id": ELECTROPLATING_SERVICE_ID,
        "material_id": "alum_D16",
        "material_form": "sheet",
        "quantity": 1,
        "file_type": "step",
        "electroplating_process_id": "titanium_passivation",
    }
    errors = validate_calculation_request(request_data)
    assert any(error.field == "electroplating_process_id" for error in errors)
