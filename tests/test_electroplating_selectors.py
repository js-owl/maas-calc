from constants import MATERIALS
from utils.electroplating_config import (
    ELECTROPLATING_SERVICE_ID,
    is_material_allowed_for_electroplating_process,
)


def test_materials_endpoint_filters_by_electroplating_process(client):
    response = client.get(
        "/materials",
        params={
            "process": ELECTROPLATING_SERVICE_ID,
            "electroplating_process_id": "galvanization_zinc_phosphating",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    material_ids = {material["id"] for material in data["materials"]}

    assert "steel_30XGSA" in material_ids
    assert "alum_D16" not in material_ids
    assert "t-10-14" not in material_ids
    assert data["electroplating_process_id"] == "galvanization_zinc_phosphating"


def test_material_forms_endpoint_returns_only_configured_forms_for_selected_material(client):
    response = client.get(
        "/material_forms",
        params={
            "service_id": ELECTROPLATING_SERVICE_ID,
            "electroplating_process_id": "galvanization_zinc_phosphating",
            "material_id": "steel_30XGSA",
        },
    )
    assert response.status_code == 200
    forms = response.json()["data"]["material_forms"]
    form_ids = {form["id"] for form in forms}

    assert form_ids == set(MATERIALS["steel_30XGSA"]["forms"].keys())


def test_material_forms_endpoint_rejects_material_not_allowed_for_selected_process(client):
    response = client.get(
        "/material_forms",
        params={
            "service_id": ELECTROPLATING_SERVICE_ID,
            "electroplating_process_id": "galvanization_zinc_phosphating",
            "material_id": "alum_D16",
        },
    )
    payload = response.json()
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert payload["details"][0]["field"] == "material_id"


def test_selector_helper_uses_explicit_family_only():
    assert is_material_allowed_for_electroplating_process(
        "steel_30XGSA",
        MATERIALS["steel_30XGSA"],
        "galvanization_zinc_phosphating",
    )
    assert not is_material_allowed_for_electroplating_process(
        "alum_D16",
        MATERIALS["alum_D16"],
        "galvanization_zinc_phosphating",
    )
