from types import SimpleNamespace

import pytest

from calculations.core import calculate_billable_material_weight
from calculators.ml_calculator import MLCNCMillingCalculator


def test_billable_material_weight_applies_moq_once_per_order():
    assert calculate_billable_material_weight(3.0, 1, 10.0)["billable_order_weight_kg"] == 10.0
    assert calculate_billable_material_weight(3.0, 2, 10.0)["billable_order_weight_kg"] == 10.0
    assert calculate_billable_material_weight(3.0, 3, 10.0)["billable_order_weight_kg"] == 10.0

    usage = calculate_billable_material_weight(3.0, 4, 10.0)
    assert usage["minimum_order_quantity_applied"] is False
    assert usage["billable_order_weight_kg"] == 12.0
    assert usage["billable_weight_per_unit_kg"] == 3.0


def test_ml_material_cost_distributes_moq_over_quantity(monkeypatch):
    calculator = MLCNCMillingCalculator()

    monkeypatch.setattr(
        "calculators.ml_calculator.get_material_info",
        lambda material_id, material_form: {
            "price": 100.0,
            "density": 2727.272727,  # 100x100x100 mm * 1.1 => about 3 kg
            "minimum_order_quantity": 10.0,
        },
    )
    monkeypatch.setattr(
        "calculators.ml_calculator.MATERIALS",
        {
            "equipment": {
                "density": 1.0,
                "forms": {"sheet": {"price": 1.0}},
            }
        },
    )
    monkeypatch.setattr("calculators.ml_calculator.SPECIAL_EQUIPMENT_MATERIAL", "equipment")
    monkeypatch.setattr("calculators.ml_calculator.SPECIAL_EQUIPMENT_FORM", "sheet")

    request = SimpleNamespace(
        service_id="cnc-milling",
        quantity=3,
        obb_x=100.0,
        obb_y=100.0,
        obb_z=100.0,
        material_id="test-material",
        material_form="sheet",
    )

    costs = calculator._calculate_material_costs(request)

    assert costs["minimum_order_quantity_applied"] is True
    assert costs["raw_estimated_weight_kg"] == pytest.approx(3.0, abs=0.01)
    assert costs["billable_order_weight_kg"] == 10.0
    assert costs["billable_weight_kg"] == pytest.approx(10.0 / 3.0, abs=1e-4)
    assert costs["material_price"] == pytest.approx(333.33, abs=0.01)
