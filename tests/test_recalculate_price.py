import pytest

from commercial_constants import COST_STRUCTURE
from constants import VAT_RATE


def test_recalculate_price_propagates_edited_work_price(client):
    payload = {
        "order_id": "order-701",
        "order_name": "Alternate pump bracket",
        "order_code": "PB-701-B",
        "service_id": "cnc-milling",
        "material_id": "non_ferrous_Д16",
        "material_form": "sheet",
        "file_id": "file-701",
        "document_ids": ["drawing-701", "spec-701"],
        "special_instructions": "Keep datum face uncoated",
        "quantity": 40,
        "k_quantity": 0.91,
        "mat_price": 120.0,
        "work_price": 300.0,
        "detail_price_one": 1.0,
        "total_price_breakdown": {
            "mat_price": 120.0,
            "work_price": 475.0,
            "price_of_hour": 732.91818,
            "dop_salary": 1.0,
            "insurance_price": 1.0,
            "overhead_expenses": 1.0,
            "administrative_expenses": 1.0,
            "net_cost": 1.0,
            "profit": 1.0,
            "cost": 1.0,
            "price_special_equipment": 800.0,
            "price_special_equipment_to_quantity": 20.0,
            "detail_price": 1.0,
        },
        "detail_price_calculation": {
            "material_price": 1.0,
            "salary_fund_with_taxes": 1.0,
            "price_special_equipment": 1.0,
            "price_without_vat": 1.0,
            "taxes": 1.0,
            "total": 2.0,
        },
    }

    response = client.post(
        "/recalculate-price",
        params={"changed_field": "total_price_breakdown.work_price"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    breakdown = data["total_price_breakdown"]
    compact = data["detail_price_calculation"]
    coefficients = COST_STRUCTURE["location_1"]

    expected_dop_salary = coefficients["dop_salary_coef"] * 475.0
    expected_insurance = coefficients["insurance_coef"] * (475.0 + expected_dop_salary)
    expected_overhead = coefficients["overhead_expenses_coef"] * 475.0
    expected_administrative = coefficients["administrative_expenses_coef"] * 475.0
    expected_net_cost = (
        120.0
        + 475.0
        + expected_dop_salary
        + expected_insurance
        + expected_overhead
        + expected_administrative
    )
    expected_profit = (
        120.0 * coefficients["profit_material"]
        + (expected_net_cost - 120.0) * coefficients["other_profit"]
    )
    expected_cost = round(expected_net_cost + expected_profit, 2)
    expected_unit_before_quantity = round(expected_cost + 20.0, 2)
    expected_unit_price = round(expected_unit_before_quantity * 0.91, 2)

    assert data["order_code"] == "PB-701-B"
    assert data["work_price"] == pytest.approx(475.0)
    assert breakdown["dop_salary"] == pytest.approx(expected_dop_salary)
    assert breakdown["insurance_price"] == pytest.approx(expected_insurance)
    assert breakdown["net_cost"] == pytest.approx(expected_net_cost)
    assert breakdown["profit"] == pytest.approx(expected_profit)
    assert breakdown["cost"] == pytest.approx(expected_cost)
    assert data["detail_price_one"] == pytest.approx(expected_unit_before_quantity)
    assert data["detail_price"] == pytest.approx(expected_unit_price)
    assert data["total_price"] == pytest.approx(round(expected_unit_price * 40, 2))
    assert compact["price_without_vat"] == pytest.approx(expected_unit_price)
    assert compact["taxes"] == pytest.approx(round(expected_unit_price * VAT_RATE, 2))
    assert compact["total"] == pytest.approx(
        round(expected_unit_price * (1 + VAT_RATE), 2)
    )

    # A later edit higher in the hierarchy must update only its direct parent.
    data["detail_price_calculation"]["taxes"] = 500.0
    tax_response = client.post(
        "/recalculate-price",
        params={"changed_field": "detail_price_calculation.taxes"},
        json=data,
    )
    tax_data = tax_response.json()["data"]
    assert tax_data["detail_price_calculation"]["total"] == pytest.approx(
        expected_unit_price + 500.0
    )
    assert tax_data["total_price_breakdown"]["cost"] == pytest.approx(expected_cost)
