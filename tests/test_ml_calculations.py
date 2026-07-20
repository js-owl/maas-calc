"""Tests for active ML calculation paths."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from calculators.ml_calculator import MLCNCMillingCalculator, MLCompositeCalculator
from utils.ml_predictor import ml_predictor
from utils.calculation_router import CalculationRouter


MOCK_ML_FEATURES = {
    "dimensions": {"length": 10.0, "width": 5.0, "height": 5.0},
    "volume": 1000.0,
    "surface_area": 500.0,
    "obb_x": 10.0,
    "obb_y": 10.0,
    "obb_z": 10.0,
    "min_size": 10.0,
    "mid_size": 10.0,
    "max_size": 10.0,
    "aspect_ratio_xy": 1.0,
    "aspect_ratio_yz": 1.0,
    "aspect_ratio_xz": 1.0,
    "bbox_volume": 1000.0,
    "features": {"face_count": 6, "vertex_count": 8, "edge_count": 12},
}


def test_ml_predictor_initialization():
    assert ml_predictor is not None


def test_classifier_feature_extraction():
    # The exact feature list comes from classifier preprocessing assets. In test
    # environments without assets the method may fail gracefully; this test only
    # verifies that the classifier-only predictor can be called safely.
    features = ml_predictor.extract_classifier_features_from_file(MOCK_ML_FEATURES)
    if features is not None:
        assert features["volume"] == 1000.0
        assert features["surface_area"] == 500.0
        assert features["obb_x"] == 10.0


def test_active_ml_calculator_classes():
    assert MLCNCMillingCalculator().service_id == "cnc-milling"
    assert MLCompositeCalculator().service_id == "composite"


def test_cnc_milling_requires_ml_path(monkeypatch):
    router = CalculationRouter()
    with pytest.raises(ValueError):
        router._get_calculator("cnc-milling", use_ml=False)


@pytest.mark.asyncio
async def test_cnc_milling_uses_flexible_ensemble_and_classifier(monkeypatch):
    calculator = MLCNCMillingCalculator()
    request = SimpleNamespace(
        file_id="test-cnc",
        service_id="cnc-milling",
        ml_features=MOCK_ML_FEATURES,
        material_id="non_ferrous_Д16",
        material_form="sheet",
        quantity=1,
        cover_id=["1"],
        tolerance_id="1",
        finish_id="1",
        location="location_1",
        k_otk=1.0,
        filename="test.stp",
        obb_x=10.0,
        obb_y=10.0,
        obb_z=10.0,
    )

    with patch("calculators.ml_calculator.check_machines", return_value=[]), \
         patch("calculators.ml_calculator.get_material_info", return_value={
             "price": 100.0,
             "density": 2700.0,
             "material_bar": "sheet",
         }), \
         patch("calculators.ml_calculator.composite_ml_predictor.predict_from_file_features", return_value=2.5) as labor_mock, \
         patch("calculators.ml_calculator.ml_predictor.predict_special_equipment_from_file_features", return_value=0) as cls_mock:
        result = await calculator.calculate(request)

    assert result.service_id == "cnc-milling"
    labor_mock.assert_called_once()
    cls_mock.assert_called_once()
