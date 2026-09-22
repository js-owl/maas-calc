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


def _snapshot_payload(**overrides):
    payload = {
        "service_id": "cnc-milling",
        "material_id": "non_ferrous_Д16",
        "material_form": "sheet",
        "k_otk": 1.0,
        "cover_id": ["1"],
        "finish_id": "1",
        "tolerance_id": "1",
        "quantity": 40,
        "k_quantity": 0.91,
        "mat_price": 120.0,
        "work_price": 475.0,
        "detail_price_one": 1.0,
        "detail_price": 1.0,
        "total_price": 40.0,
        "total_price_breakdown": {
            "mat_price": 120.0,
            "work_price": 475.0,
            "price_of_hour": 732.91818,
            "dop_salary": 47.5,
            "insurance_price": 157.795,
            "overhead_expenses": 407.2175,
            "administrative_expenses": 408.12,
            "net_cost": 1615.6325,
            "profit": 375.108125,
            "cost": 1990.74,
            "is_need_special_equipment": True,
            "material_price_special_equipment": 250.0,
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
    payload.update(overrides)
    return payload


def test_edited_nested_work_price_is_source_of_truth():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload(work_price=300.0)
    result = recalculate_price_snapshot(payload, "total_price_breakdown.work_price")

    assert result["work_price"] == pytest.approx(475.0)
    assert result["total_price_breakdown"]["work_price"] == pytest.approx(475.0)
    coefficients = COST_STRUCTURE["location_1"]
    assert result["total_price_breakdown"]["dop_salary"] == pytest.approx(
        coefficients["dop_salary_coef"] * 475.0
    )


def test_unrelated_edit_does_not_clobber_nested_work_price_with_stale_top_level():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload(work_price=300.0)
    payload["total_price_breakdown"]["dop_salary"] = 400.0

    result = recalculate_price_snapshot(payload, "total_price_breakdown.dop_salary")
    breakdown = result["total_price_breakdown"]
    coefficients = COST_STRUCTURE["location_1"]

    assert breakdown["dop_salary"] == pytest.approx(400.0)
    assert breakdown["work_price"] == pytest.approx(475.0)
    assert result["work_price"] == pytest.approx(475.0)
    assert breakdown["insurance_price"] == pytest.approx(
        coefficients["insurance_coef"] * (475.0 + 400.0)
    )


def test_unrelated_edit_does_not_clobber_nested_mat_price_with_stale_top_level():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload(mat_price=10.0)
    payload["total_price_breakdown"]["net_cost"] = 5000.0
    coefficients = COST_STRUCTURE["location_1"]

    result = recalculate_price_snapshot(payload, "total_price_breakdown.net_cost")
    breakdown = result["total_price_breakdown"]

    assert breakdown["net_cost"] == pytest.approx(5000.0)
    assert breakdown["mat_price"] == pytest.approx(120.0)
    assert result["mat_price"] == pytest.approx(120.0)
    assert breakdown["profit"] == pytest.approx(
        120.0 * coefficients["profit_material"]
        + (5000.0 - 120.0) * coefficients["other_profit"]
    )


def test_mat_price_edit_fills_missing_labor_lines_before_net_cost():
    from calculations.core import calculate_cost
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = {
        "service_id": "cnc-milling",
        "material_id": "non_ferrous_Д16",
        "material_form": "sheet",
        "k_otk": 1.0,
        "cover_id": ["1"],
        "finish_id": "1",
        "tolerance_id": "1",
        "total_time": 0.65,
        "quantity": 40,
        "k_quantity": 0.91,
        "mat_price": 999.0,
        "work_price": 475.0,
        "total_price_breakdown": {
            "mat_price": 120.0,
            "total_time": 0.65,
            "price_of_hour": 732.91818,
            "work_price": 475.0,
            "is_need_special_equipment": True,
            "material_price_special_equipment": 250.0,
            "price_special_equipment": 800.0,
            "price_special_equipment_to_quantity": 20.0,
        },
        "detail_price_calculation": {
            "material_price": 0.0,
            "salary_fund_with_taxes": 0.0,
            "price_special_equipment": 0.0,
            "price_without_vat": 0.0,
            "taxes": 0.0,
            "total": 0.0,
        },
    }

    result = recalculate_price_snapshot(payload, "mat_price")
    expected_net = calculate_cost(999.0, 475.0, "location_1", breakdown=True)[1]["net_cost"]

    assert result["mat_price"] == pytest.approx(999.0)
    assert result["total_price_breakdown"]["mat_price"] == pytest.approx(999.0)
    assert result["total_price_breakdown"]["net_cost"] == pytest.approx(expected_net)
    assert result["total_price_breakdown"]["dop_salary"] == pytest.approx(47.5)


def test_top_level_detail_price_propagates_to_nested_and_compact():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload(detail_price=2222.0)
    result = recalculate_price_snapshot(payload, "detail_price")

    assert result["detail_price"] == pytest.approx(2222.0)
    assert result["total_price_breakdown"]["detail_price"] == pytest.approx(2222.0)
    assert result["detail_price_calculation"]["price_without_vat"] == pytest.approx(2222.0)
    assert result["total_price"] == pytest.approx(round(2222.0 * 40, 2))
    assert result["detail_price_one"] == pytest.approx(round(2222.0 / 0.91, 2))


def test_price_of_hour_edit_rebuilds_work_price_and_hour_with_others():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload()
    payload["total_time"] = 2.0
    payload["total_price_breakdown"]["total_time"] = 2.0
    payload["total_price_breakdown"]["price_of_hour"] = 1000.0
    payload["total_price_breakdown"]["price_of_hour_with_others"] = 1.0

    result = recalculate_price_snapshot(payload, "total_price_breakdown.price_of_hour")
    breakdown = result["total_price_breakdown"]
    coefficients = COST_STRUCTURE["location_1"]
    cover = 1.05
    tolerance = 1.15
    finish = 0.9
    expected_work = 2.0 * 1000.0 * 1.0 * cover * tolerance * finish
    hour_multiplier = (
        1
        + coefficients["dop_salary_coef"]
        + coefficients["dop_salary_coef"] * coefficients["insurance_coef"]
        + coefficients["insurance_coef"]
        + coefficients["overhead_expenses_coef"]
        + coefficients["administrative_expenses_coef"]
    )

    assert breakdown["price_of_hour"] == pytest.approx(1000.0)
    assert result["work_price"] == pytest.approx(expected_work)
    assert breakdown["work_price"] == pytest.approx(expected_work)
    assert breakdown["price_of_hour_with_others"] == pytest.approx(round(1000.0 * hour_multiplier, 2))


def test_total_price_propagates_to_unit_price():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload(total_price=80000.0)
    result = recalculate_price_snapshot(payload, "total_price")
    expected_detail = round(80000.0 / 40, 2)

    assert result["total_price"] == pytest.approx(80000.0)
    assert result["detail_price"] == pytest.approx(expected_detail)
    assert result["total_price_breakdown"]["detail_price"] == pytest.approx(expected_detail)
    assert result["detail_price_calculation"]["price_without_vat"] == pytest.approx(expected_detail)


def test_equipment_unit_edit_updates_total_and_price_graph():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload()
    payload["total_price_breakdown"]["price_special_equipment_to_quantity"] = 30.0

    result = recalculate_price_snapshot(
        payload,
        "total_price_breakdown.price_special_equipment_to_quantity",
    )

    assert result["total_price_breakdown"]["price_special_equipment"] == pytest.approx(1200.0)
    assert result["detail_price_one"] == pytest.approx(
        round(result["total_price_breakdown"]["cost"] + 30.0, 2)
    )


def test_compact_component_edit_uses_reverse_unit_route():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload()
    payload["detail_price_calculation"]["material_price"] = 200.0

    result = recalculate_price_snapshot(
        payload,
        "detail_price_calculation.material_price",
    )

    expected_detail = 202.0
    assert result["detail_price"] == pytest.approx(expected_detail)
    assert result["total_price_breakdown"]["detail_price"] == pytest.approx(expected_detail)
    assert result["total_price"] == pytest.approx(expected_detail * 40)


def test_geometry_edit_runs_material_downstream_graph():
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload(
        length=100.0,
        width=50.0,
        height=20.0,
        mat_volume=0.0,
        mat_weight=0.0,
    )

    result = recalculate_price_snapshot(payload, "length")

    assert result["mat_volume"] == pytest.approx(0.0001)
    assert result["mat_weight"] >= 0.0
    assert result["total_price_breakdown"]["net_cost"] > 0.0


@pytest.mark.parametrize("field", ["order_code", "special_instructions", "file_id"])
def test_passthrough_edit_preserves_snapshot(field):
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload()
    payload[field] = "updated"

    assert recalculate_price_snapshot(payload, field) == payload


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("unknown", 1.0),
        ("too.deep.path", 1.0),
        ("mat_price", None),
    ],
)
def test_invalid_changed_field_is_rejected(field, value):
    from calculations.price_recalculation import recalculate_price_snapshot

    payload = _snapshot_payload()
    if field == "mat_price":
        payload[field] = value

    with pytest.raises(ValueError):
        recalculate_price_snapshot(payload, field)
