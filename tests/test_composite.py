from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pandas as pd

from calculators.ml_calculator import MLCompositeCalculator
from utils.composite_ml_predictor import CompositeMLPredictor


class _FakeTrainer:
    def predict(self, df: pd.DataFrame, include_detail_columns: bool = False) -> pd.DataFrame:
        assert include_detail_columns is False
        assert len(df) == 1
        return pd.DataFrame([{"ensemble": 3.5}])


def test_composite_material_cost_uses_layer_thickness_and_margin():
    calc = MLCompositeCalculator()
    request = SimpleNamespace(
        material_id="pre-preg_v180",
        material_form="textile",
        ml_features={"volume": 1000000.0},
    )

    costs = calc._calculate_composite_material_costs(request)

    assert costs["one_layer_thickness_mm"] == 0.2
    assert costs["price_per_square_meter"] == 4930.0
    assert costs["layer_count"] == 6
    assert costs["volume_with_margin_m3"] == 0.0011
    assert costs["required_stack_thickness_mm"] == 1.1


def test_ml_composite_calculator_returns_composite_response(monkeypatch):
    calc = MLCompositeCalculator()
    monkeypatch.setattr(
        "calculators.ml_calculator.composite_ml_predictor.predict_from_file_features",
        lambda file_features, material_info: 2.0,
    )

    request = SimpleNamespace(
        file_id="file-1",
        filename="part.step",
        ml_features={
            "volume": 1000000.0,
            "surface_area": 2500.0,
            "obb_x": 100.0,
            "obb_y": 50.0,
            "obb_z": 20.0,
            "dimensions": None,
        },
        material_id="pre-preg_v180",
        material_form="textile",
        location="location_1",
        quantity=2,
        cover_id=["1"],
        k_otk=1.0,
        service_id="composite",
    )

    response = asyncio.run(calc.calculate(request))

    assert response.service_id == "composite"
    assert response.calculation_engine == "ml_model"
    assert response.ml_prediction_hours == 2.0
    assert response.total_time == 2.0
    assert response.material_costs["layer_count"] == 6
    assert response.total_price > 0
