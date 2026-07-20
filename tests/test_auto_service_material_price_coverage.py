"""Coverage tests for auto-service material pricing inputs.

These tests protect against stale frontend defaults such as material_form="sheet"
being sent for cnc-milling materials that are priced only as rod.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

import commercial_constants

# Slim archives used in CI/review may omit confidential pricing/machine tables.
# These tests exercise public material-form fallback logic and only need minimal
# stubs for modules that import calculations.core / ml_calculator.
if not hasattr(commercial_constants, "COST_STRUCTURE"):
    commercial_constants.COST_STRUCTURE = {
        "location_1": {
            "price_of_hour": 1000.0,
            "dop_salary_coef": 0.0,
            "insurance_coef": 0.0,
            "overhead_expenses_coef": 0.0,
            "administrative_expenses_coef": 0.0,
            "profit_material": 0.2,
            "other_profit": 0.3,
        }
    }
if not hasattr(commercial_constants, "MACHINES"):
    commercial_constants.MACHINES = {
        "test_mill": {
            "type": "milling",
            "location": "location_1",
            "max_x": 10_000.0,
            "max_y": 10_000.0,
            "max_z": 10_000.0,
            "name": "test_mill",
        }
    }

from MATERIALS_gen import MATERIALS
from calculations.core import get_material_info, resolve_material, resolve_priced_material_form
from calculators.ml_calculator import MLCNCMillingCalculator, MLCompositeCalculator
from utils.validation_utils import validate_calculation_request


def _selectable_material_forms(service_id: str):
    for material_id, material in MATERIALS.items():
        if service_id not in material.get("applicable_processes", []):
            continue
        for form_id, form in (material.get("forms") or {}).items():
            if service_id in (form.get("applicable_processes") or []):
                yield material_id, form_id, form


@pytest.mark.parametrize("material_id", [
    material_id
    for material_id, material in MATERIALS.items()
    if "cnc-milling" in material.get("applicable_processes", [])
])
def test_cnc_milling_all_selectable_materials_get_positive_material_price_even_with_sheet_default(material_id):
    request = SimpleNamespace(
        service_id="cnc-milling",
        quantity=1,
        obb_x=100.0,
        obb_y=50.0,
        obb_z=10.0,
        material_id=material_id,
        material_form="sheet",
    )

    costs = MLCNCMillingCalculator()._calculate_material_costs(request)

    assert costs["material_form"] in MATERIALS[material_id]["forms"]
    assert costs["price_per_kg"] > 0
    assert costs["material_price"] > 0


@pytest.mark.parametrize("service_id,material_id,form_id,form", [
    (service_id, material_id, form_id, form)
    for service_id in ("printing", "cnc-milling", "composite")
    for material_id, form_id, form in _selectable_material_forms(service_id)
])
def test_all_selectable_auto_service_material_forms_have_positive_price(service_id, material_id, form_id, form):
    assert form.get("price", 0) > 0, (service_id, material_id, form_id)


@pytest.mark.parametrize("material_id,form_id,form", list(_selectable_material_forms("printing")))
def test_printing_selectable_material_forms_resolve_to_positive_price(material_id, form_id, form):
    resolved = resolve_material(material_id, form_id, "printing")
    assert resolved["price"] > 0


@pytest.mark.parametrize("material_id,form_id,form", list(_selectable_material_forms("composite")))
def test_composite_selectable_material_forms_calculate_positive_material_price(material_id, form_id, form):
    request = SimpleNamespace(
        material_id=material_id,
        material_form=form_id,
        ml_features={"volume": 100_000.0},
    )

    costs = MLCompositeCalculator()._calculate_composite_material_costs(request)

    assert costs["price_per_square_meter"] > 0
    assert costs["material_price"] > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("material_id", [
    material_id
    for material_id, material in MATERIALS.items()
    if "cnc-milling" in material.get("applicable_processes", [])
])
async def test_cnc_milling_all_selectable_materials_return_positive_total_price_with_sheet_default(material_id):
    request = SimpleNamespace(
        file_id=f"cnc-{material_id}",
        service_id="cnc-milling",
        ml_features={
            "dimensions": {"length": 100.0, "width": 50.0, "height": 10.0},
            "volume": 50_000.0,
            "surface_area": 10_000.0,
            "obb_x": 100.0,
            "obb_y": 50.0,
            "obb_z": 10.0,
        },
        material_id=material_id,
        material_form="sheet",  # stale frontend default; must not force zero price
        quantity=1,
        cover_id=["1"],
        tolerance_id="1",
        finish_id="1",
        location="location_1",
        k_otk=1.0,
        filename="test.step",
        obb_x=100.0,
        obb_y=50.0,
        obb_z=10.0,
    )

    with patch("calculators.ml_calculator.check_machines", return_value=["test_mill"]), \
         patch("calculators.ml_calculator.composite_ml_predictor.predict_from_file_features", return_value=1.0), \
         patch("calculators.ml_calculator.ml_predictor.predict_special_equipment_from_file_features", return_value=0):
        result = await MLCNCMillingCalculator().calculate(request)

    assert result.total_price > 0
    assert result.detail_price > 0
    assert result.material_costs["material_price"] > 0
    assert result.total_price_breakdown["price_per_kg"] > 0


def _first_form_id(material_id: str) -> str:
    forms = MATERIALS[material_id].get("forms") or {}
    assert forms, f"Material {material_id} must have at least one form for validation test"
    return next(iter(forms.keys()))


def _invalid_material_cases_for_material_based_auto_services():
    """Return one intentionally invalid material for each material-based auto service.

    Electroplating is intentionally not included here: it is selected by
    electroplating_family/process compatibility rather than MATERIALS[*]
    applicable_processes. It has a dedicated test below.
    """
    preferred_materials = {
        "printing": "steel_0001",      # CNC material, not printable powder
        "cnc-milling": "PA12",         # printing powder, not CNC stock
        "composite": "PA12",           # printing powder, not composite fabric/prepreg
    }
    cases = []
    for service_id, preferred_material_id in preferred_materials.items():
        material_id = None
        if preferred_material_id in MATERIALS and service_id not in MATERIALS[preferred_material_id].get("applicable_processes", []):
            material_id = preferred_material_id
        else:
            for candidate_id, material in MATERIALS.items():
                if candidate_id == "other":
                    continue
                if service_id not in material.get("applicable_processes", []):
                    material_id = candidate_id
                    break
        assert material_id is not None, f"No invalid material found for service_id={service_id}"
        cases.append((service_id, material_id, _first_form_id(material_id)))
    return cases


@pytest.mark.parametrize(
    "service_id,material_id,material_form",
    _invalid_material_cases_for_material_based_auto_services(),
)
def test_material_based_auto_services_reject_materials_not_applicable_to_service(
    service_id,
    material_id,
    material_form,
):
    material_processes = MATERIALS[material_id].get("applicable_processes", [])
    assert service_id not in material_processes

    errors = validate_calculation_request({
        "service_id": service_id,
        "material_id": material_id,
        "material_form": material_form,
        "quantity": 1,
        "file_type": "step",
    })

    assert any(error.field == "material_id" for error in errors), (
        service_id,
        material_id,
        material_processes,
        [(error.field, error.message) for error in errors],
    )


def test_material_applicability_validation_runs_before_cnc_material_form_fallback():
    """PA12 must not become valid for CNC just because it has a priced powder form.

    This protects the sheet/rod fallback from accidentally broadening the
    material itself to services outside MATERIALS[*].applicable_processes.
    """
    errors = validate_calculation_request({
        "service_id": "cnc-milling",
        "material_id": "PA12",
        "material_form": "powder",
        "quantity": 1,
        "file_type": "step",
    })

    assert any(error.field == "material_id" for error in errors)


def test_electroplating_auto_rejects_non_galvanic_material():
    """Electroplating uses material families, but non-galvanic materials still fail."""
    errors = validate_calculation_request({
        "service_id": "electroplating_auto",
        "material_id": "PA12",
        "material_form": "powder",
        "quantity": 1,
        "file_type": "step",
        "electroplating_process_id": "galvanization_zinc_phosphating",
    })

    assert any(error.field == "material_id" for error in errors)

