"""Tests for the unified auto-service pricing pipeline."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from calculations.core import build_unified_unit_price
from commercial_constants import COST_STRUCTURE
from constants import VAT_RATE
from calculators.ml_calculator import MLCNCMillingCalculator, MLCompositeCalculator
from calculators.printing_calculator import PrintingCalculator
from calculators.electroplating_calculator import ElectroplatingAutoCalculator
from models.base_models import Dimensions
from models.calculation_models import PrintingCalculationRequest


def assert_compact_calculation_matches_response(response):
    compact = response.detail_price_calculation
    assert compact is not None
    for field in (
        "material_price",
        "salary_fund_with_taxes",
        "price_special_equipment",
        "price_without_vat",
        "taxes",
        "total",
    ):
        assert field in compact
        assert compact[field] >= 0

    assert compact["price_without_vat"] == pytest.approx(response.detail_price)
    assert compact["taxes"] == pytest.approx(round(response.detail_price * VAT_RATE, 2))
    assert compact["total"] == pytest.approx(round(response.detail_price * (1 + VAT_RATE), 2))
    assert (
        compact["material_price"]
        + compact["salary_fund_with_taxes"]
        + compact["price_special_equipment"]
    ) == pytest.approx(response.detail_price, abs=0.03)


def test_unified_unit_price_applies_quantity_deflator_after_tooling():
    pricing = build_unified_unit_price(
        mat_price=100.0,
        work_price=200.0,
        location="location_1",
        quantity=10,
        k_quantity=0.9,
        price_special_equipment_to_quantity=50.0,
    )

    base_cost = pricing["base_cost"]
    assert pricing["detail_price_one"] == pytest.approx(base_cost + 50.0)
    assert pricing["detail_price"] == pytest.approx(round((base_cost + 50.0) * 0.9, 2))
    assert pricing["total_price"] == pytest.approx(round(pricing["detail_price"] * 10, 2))
    assert pricing["detail_price_calculation"]["price_special_equipment"] == pytest.approx(round(50.0 * 0.9, 2))


@pytest.mark.asyncio
async def test_printing_uses_unified_price_structure():
    request = PrintingCalculationRequest(
        file_id="print-price-structure",
        dimensions=Dimensions(length=100, width=50, height=10),
        material_id="plastic_PETG",
        material_form="thread",
        quantity=25,
        cover_id=["1"],
        location="location_3",
        k_otk=1.0,
        k_cert=["a"],
        service_id="printing",
    )

    response = await PrintingCalculator().calculate(request)

    assert response.total_price_breakdown["price_special_equipment_to_quantity"] == 0.0
    assert response.detail_price == pytest.approx(
        round(response.detail_price_one * response.k_quantity, 2)
    )
    assert_compact_calculation_matches_response(response)


@pytest.mark.asyncio
async def test_cnc_milling_uses_unified_price_structure_with_tooling():
    request = SimpleNamespace(
        file_id="cnc-price-structure",
        service_id="cnc-milling",
        ml_features={
            "dimensions": {"length": 100.0, "width": 50.0, "height": 10.0},
            "volume": 50_000.0,
            "surface_area": 10_000.0,
            "obb_x": 100.0,
            "obb_y": 50.0,
            "obb_z": 10.0,
        },
        material_id="non_ferrous_Д16",
        material_form="sheet",
        quantity=25,
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
         patch("calculators.ml_calculator.ml_predictor.predict_special_equipment_from_file_features", return_value=1):
        response = await MLCNCMillingCalculator().calculate(request)

    assert response.total_price_breakdown["price_special_equipment_to_quantity"] > 0
    assert response.detail_price == pytest.approx(
        round(response.detail_price_one * response.k_quantity, 2)
    )
    assert_compact_calculation_matches_response(response)


@pytest.mark.asyncio
async def test_composite_uses_unified_price_structure():
    request = SimpleNamespace(
        file_id="composite-price-structure",
        service_id="composite",
        ml_features={
            "dimensions": {"length": 100.0, "width": 50.0, "height": 10.0},
            "volume": 50_000.0,
            "surface_area": 10_000.0,
            "obb_x": 100.0,
            "obb_y": 50.0,
            "obb_z": 10.0,
        },
        material_id="carbon_fiber_0011",
        material_form="textile",
        quantity=25,
        cover_id=["1"],
        location="location_1",
        k_otk=1.0,
        is_need_special_equipment=1,
        filename="test.step",
    )

    with patch("calculators.ml_calculator.composite_ml_predictor.predict_from_file_features", return_value=1.0):
        response = await MLCompositeCalculator().calculate(request)

    assert response.total_price_breakdown["price_special_equipment_to_quantity"] > 0
    assert response.detail_price == pytest.approx(
        round(response.detail_price_one * response.k_quantity, 2)
    )
    assert_compact_calculation_matches_response(response)


@pytest.mark.asyncio
async def test_electroplating_uses_unified_price_structure(monkeypatch):
    fake_process = {
        "layout": {
            "requested_quantity": 25,
            "batch_quantity": 5,
            "batch_capacity": 5,
            "geometric_capacity": 10,
            "practical_geometric_capacity": 5,
            "current_capacity": 99,
            "weight_capacity": 99,
            "max_weight_kg": 20.0,
            "requested_total_weight_kg": 2.5,
            "batch_weight_kg": 0.5,
            "batch_count": 5,
            "batch_quantity_limited_by": "geometry",
        },
        "labor_time_hours": 0.5,
        "labor_time_min": 30.0,
        "order_labor_time_hours": 12.5,
        "order_labor_time_min": 750.0,
        "per_detail_operation_labor_min": 10.0,
        "operation_time_min": 20.0,
        "operation_time_component_min": 0.0,
        "coating_time_min": 0.0,
        "preparation_time_min": 20.0,
        "workers_count": 1,
        "mount_unmount_time_min": 2.5,
        "time_model": "fixed_time",
        "thickness_role": "not_applicable",
        "process": {"id": "silvering", "label": "Silvering"},
        "material_family": {"id": "copper"},
        "geometry": {
            "surface_area_mm2": 1000.0,
            "surface_area_dm2": 1.0,
            "volume_mm3": 1000.0,
            "volume_dm3": 0.001,
        },
        "part_weight_kg": 0.1,
        "dimensions_mm": [10.0, 10.0, 10.0],
    }
    monkeypatch.setattr(
        "calculators.electroplating_calculator.calculate_electroplating_parameters",
        lambda **kwargs: fake_process,
    )

    request = SimpleNamespace(
        file_id="ep-price-structure",
        filename="test.step",
        service_id="electroplating_auto",
        ml_features={"volume": 1000.0},
        material_id="non_ferrous_Л63",
        material_form="sheet",
        electroplating_family="copper",
        quantity=25,
        location="location_1",
        cover_id=[],
        electroplating_process_id="silvering",
        coating_thickness_microns=None,
        processing_depth_microns=None,
        k_otk=1.0,
    )

    response = await ElectroplatingAutoCalculator().calculate(request)

    assert response.total_price_breakdown["price_special_equipment_to_quantity"] == 0.0
    assert response.detail_price == pytest.approx(
        round(response.detail_price_one * response.k_quantity, 2)
    )
    assert_compact_calculation_matches_response(response)
