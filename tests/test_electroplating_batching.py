import pytest

from constants import ELECTROPLATING_LABOR_TIME_COEF

from calculations.electroplating import calculate_electroplating_parameters
from utils.electroplating_config import get_electroplating_process, get_process_params


def _expected_practical_capacity(ep, geometric_capacity: int) -> int:
    return max(1, int(geometric_capacity * ep.PRACTICAL_GEOMETRIC_CAPACITY_FACTOR))


def _features():
    return {
        "surface_area": 60_000.0,  # 6 dm²
        "volume": 100_000.0,       # 0.1 dm³ -> 0.78 kg for steel
        "obb_x": 100.0,
        "obb_y": 100.0,
        "obb_z": 100.0,
    }


def _material_info():
    return {"electroplating_family": "carbon_steel"}


def test_electroplating_config_uses_non_auto_services_operations():
    processes = get_process_params()

    assert "galvanization_zinc_phosphating" in processes
    assert "chrome_plating" in processes
    assert processes["galvanization_zinc_phosphating"]["max_part_size_mm"] == (2800.0, 700.0, 1000.0)
    assert processes["galvanization_zinc_phosphating"]["max_weight_kg"] == 400.0
    assert get_electroplating_process("zinc")["id"] == "galvanization_zinc_phosphating"


def test_electroplating_uses_bath_capacity_as_formula_n():
    params = calculate_electroplating_parameters(
        features=_features(),
        material_id="steel_test",
        material_info=_material_info(),
        process_id="zinc",
        cover_id=None,
        coating_thickness_microns=9.0,
        quantity=10,
    )

    layout = params["layout"]
    assert layout["requested_quantity"] == 10
    assert layout["batch_quantity"] == layout["batch_capacity"]
    assert params["labor_formula_batch_quantity_n"] == float(layout["batch_capacity"])


def test_electroplating_caps_formula_n_by_one_bath_capacity():
    params = calculate_electroplating_parameters(
        features=_features(),
        material_id="steel_test",
        material_info=_material_info(),
        process_id="zinc",
        cover_id=None,
        coating_thickness_microns=9.0,
        quantity=200,
    )

    layout = params["layout"]
    assert layout["requested_quantity"] == 200
    assert layout["current_capacity"] == 100
    assert layout["weight_capacity"] > layout["current_capacity"]
    assert layout["batch_capacity"] == min(
        layout["practical_geometric_capacity"],
        layout["current_capacity"],
        layout["weight_capacity"],
    )
    assert layout["batch_quantity"] == layout["batch_capacity"]
    assert layout["batch_count"] == (200 + layout["batch_capacity"] - 1) // layout["batch_capacity"]
    assert params["labor_formula_batch_quantity_n"] == float(layout["batch_capacity"])


def test_electroplating_caps_formula_n_by_bath_max_weight(monkeypatch):
    import calculations.electroplating as ep

    monkeypatch.setattr(ep, "PRACTICAL_GEOMETRIC_CAPACITY_FACTOR", 1.0)

    features = {
        "surface_area": 10_000.0,  # 1 dm² -> chrome current capacity 50
        "volume": 256_410.2564,    # ~0.256 dm³ -> ~2 kg for steel
        "obb_x": 50.0,
        "obb_y": 50.0,
        "obb_z": 50.0,
    }

    params = calculate_electroplating_parameters(
        features=features,
        material_id="steel_test",
        material_info=_material_info(),
        process_id="chrome_plating",
        cover_id=None,
        coating_thickness_microns=9.0,
        quantity=20,
    )

    layout = params["layout"]
    assert layout["max_weight_kg"] == 10.0
    assert layout["weight_capacity"] == 5
    assert layout["current_capacity"] == 50
    assert layout["batch_capacity"] == 5
    assert layout["batch_quantity"] == 5
    assert layout["batch_quantity_limited_by"] == "weight"
    assert layout["batch_weight_kg"] == pytest.approx(10.0, abs=0.01)
    assert layout["batch_count"] == 4


def test_bath_layout_geometric_capacity_rotates_hanging_plane_projection(monkeypatch):
    """A synthetic bath/part pair with clearance=0 should fit exactly 10 parts on the ideal plane."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"layout_test": {"length": 100.0, "width": 100.0, "height": 10.0, "max_weight_kg": 1_000.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(50.0, 20.0, 10.0),
        process={"id": "layout_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=10,
    )

    expected_practical = _expected_practical_capacity(ep, layout["geometric_capacity"])
    assert layout["geometric_capacity"] == 10
    assert layout["practical_geometric_capacity"] == expected_practical
    assert layout["batch_capacity"] == expected_practical
    assert layout["batch_quantity"] == expected_practical
    assert layout["batch_count"] == (10 + expected_practical - 1) // expected_practical
    assert layout["batch_quantity_limited_by"] == "geometry"
    assert layout["layout"]["counts"] in (
        {"x": 2, "y": 5, "z": 1},
        {"x": 5, "y": 2, "z": 1},
    )


def test_bath_layout_uses_two_largest_part_dimensions_as_hanging_plane(monkeypatch):
    """A thin plate must not be packed on the bath plane by its thickness.

    For a 500x500x10 part in a 1000x1000x1000 bath, the suspended projection is
    500x500. The ideal capacity is therefore 2x2=4, not 200 parts from an
    optimistic 500x10 projection.
    """
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"plate_test": {"length": 1000.0, "width": 1000.0, "height": 1000.0, "max_weight_kg": 1_000.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(500.0, 500.0, 10.0),
        process={"id": "plate_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=10,
    )

    expected_practical = _expected_practical_capacity(ep, layout["geometric_capacity"])
    assert layout["layout"]["packing_model"] == "hanging_plane"
    assert layout["layout"]["orientation_mm"] == {"x": 500.0, "y": 500.0, "z": 10.0}
    assert layout["layout"]["counts"] == {"x": 2, "y": 2, "z": 1}
    assert layout["geometric_capacity"] == 4
    assert layout["practical_geometric_capacity"] == expected_practical
    assert layout["batch_capacity"] == expected_practical
    assert layout["batch_quantity"] == expected_practical


def test_single_quantity_uses_real_bath_capacity_when_clearance_layout_fits(monkeypatch):
    """quantity=1 must still use the real one-bath capacity as formula n."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"single_capacity_test": {"length": 1000.0, "width": 1000.0, "height": 1000.0, "max_weight_kg": 1_000.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})
    monkeypatch.setattr(ep, "PRACTICAL_GEOMETRIC_CAPACITY_FACTOR", 0.10)

    layout_one = ep.calculate_bath_layout(
        dimensions_mm=(100.0, 100.0, 100.0),
        process={"id": "single_capacity_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=1,
    )
    layout_two = ep.calculate_bath_layout(
        dimensions_mm=(100.0, 100.0, 100.0),
        process={"id": "single_capacity_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=2,
    )

    assert layout_one["layout"]["packing_model"] == "hanging_plane"
    assert layout_one["geometric_capacity"] == 100
    assert layout_one["practical_geometric_capacity"] == 10
    assert layout_one["batch_capacity"] == 10
    assert layout_one["batch_quantity"] == 10
    assert layout_one["batch_count"] == 1

    assert layout_two["batch_capacity"] == layout_one["batch_capacity"]
    assert layout_two["batch_quantity"] == layout_one["batch_quantity"]
    assert layout_two["batch_count"] == 1


def test_bath_layout_checks_smallest_part_dimension_against_bath_depth(monkeypatch):
    """The smallest dimension is treated as depth and must fit the bath depth."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"depth_test": {"length": 1000.0, "width": 1000.0, "height": 15.0, "max_weight_kg": 1_000.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    with pytest.raises(ValueError, match="does not fit"):
        ep.calculate_bath_layout(
            dimensions_mm=(500.0, 100.0, 20.0),
            process={"id": "depth_test", "is_electrolytic": False},
            surface_area_dm2=1.0,
            part_weight_kg=1.0,
            quantity=1,
        )


def test_single_quantity_falls_back_without_clearance_when_clearance_layout_does_not_fit(monkeypatch):
    """For quantity=1, fallback checks one part against bath dimensions without clearance."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"single_test": {"length": 150.0, "width": 150.0, "height": 30.0, "max_weight_kg": 10.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 50.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process={"id": "single_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=1,
    )

    assert layout["layout"]["packing_model"] == "single_part_fit"
    assert layout["clearance_mm"] == 0.0
    assert layout["configured_clearance_mm"] == 50.0
    assert layout["batch_capacity"] == 1
    assert layout["batch_quantity"] == 1
    assert layout["batch_count"] == 1
    assert layout["batch_quantity_limited_by"] == "single_part"


def test_single_quantity_layout_checks_sorted_dimensions(monkeypatch):
    """Single-part fit should allow orientation by sorted OBB/bath dimensions."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"sorted_single_test": {"length": 50.0, "width": 100.0, "height": 10.0, "max_weight_kg": 10.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 50.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(100.0, 10.0, 10.0),
        process={"id": "sorted_single_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=1,
    )

    assert layout["layout"]["orientation_mm"] == {"x": 100.0, "y": 10.0, "z": 10.0}
    assert layout["layout"]["bath_dimensions_sorted_mm"] == {"x": 100.0, "y": 50.0, "z": 10.0}
    assert layout["batch_quantity"] == 1


def test_single_quantity_layout_still_checks_weight_limit(monkeypatch):
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"single_weight_test": {"length": 1000.0, "width": 1000.0, "height": 1000.0, "max_weight_kg": 10.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    with pytest.raises(ValueError, match="max_weight_kg"):
        ep.calculate_bath_layout(
            dimensions_mm=(10.0, 10.0, 10.0),
            process={"id": "single_weight_test", "is_electrolytic": False, "max_weight_kg": 10.0},
            surface_area_dm2=1.0,
            part_weight_kg=11.0,
            quantity=1,
        )


@pytest.mark.parametrize("quantity", [2, 5])
def test_multi_quantity_falls_back_to_one_part_per_batch_when_clearance_layout_does_not_fit(monkeypatch, quantity):
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"multi_clearance_test": {"length": 150.0, "width": 150.0, "height": 30.0, "max_weight_kg": 10.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 50.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process={"id": "multi_clearance_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=quantity,
    )

    assert layout["layout"]["packing_model"] == "single_part_batches"
    assert layout["layout"]["single_part_reason"] == "hanging_plane_with_clearance_has_zero_capacity"
    assert layout["clearance_mm"] == 0.0
    assert layout["configured_clearance_mm"] == 50.0
    assert layout["batch_capacity"] == 1
    assert layout["batch_quantity"] == 1
    assert layout["batch_count"] == quantity
    assert layout["batch_quantity_limited_by"] == "single_part_batches"


def test_bath_layout_weight_limit_uses_total_weight_of_parts_in_one_bath(monkeypatch):
    """Weight capacity must be floor(max_weight_kg / part_weight_kg)."""
    import calculations.electroplating as ep

    monkeypatch.setattr(ep, "PRACTICAL_GEOMETRIC_CAPACITY_FACTOR", 1.0)
    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"weight_test": {"length": 1000.0, "width": 1000.0, "height": 1000.0, "max_weight_kg": 10.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    layout = ep.calculate_bath_layout(
        dimensions_mm=(10.0, 10.0, 10.0),
        process={"id": "weight_test", "is_electrolytic": False},
        surface_area_dm2=1.0,
        part_weight_kg=2.1,
        quantity=20,
    )

    assert layout["geometric_capacity"] > 20
    assert layout["practical_geometric_capacity"] > 20
    assert layout["weight_capacity"] == 4
    assert layout["batch_capacity"] == 4
    assert layout["batch_quantity"] == 4
    assert layout["batch_weight_kg"] == pytest.approx(8.4)
    assert layout["batch_quantity_limited_by"] == "weight"
    assert layout["batch_count"] == 5


def test_order_labor_multiplies_per_detail_labor_by_requested_quantity(monkeypatch):
    """One extra part beyond capacity uses the same formula n and scales linearly."""
    import calculations.electroplating as ep

    monkeypatch.setattr(
        ep,
        "get_baths",
        lambda: {"linear_test": {"length": 500.0, "width": 200.0, "height": 10.0, "max_weight_kg": 1_000.0}},
    )
    monkeypatch.setattr(ep, "get_defaults", lambda: {"clearance_mm": 0.0, "mount_unmount_time_min": 0.0})

    process = {"id": "linear_test", "is_electrolytic": False}
    seed_layout = ep.calculate_bath_layout(
        dimensions_mm=(50.0, 20.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=2,
    )
    batch_capacity = seed_layout["batch_capacity"]
    q_before = batch_capacity
    q_after = batch_capacity + 1
    layout_before = ep.calculate_bath_layout(
        dimensions_mm=(50.0, 20.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=q_before,
    )
    layout_after = ep.calculate_bath_layout(
        dimensions_mm=(50.0, 20.0, 10.0),
        process=process,
        surface_area_dm2=1.0,
        part_weight_kg=1.0,
        quantity=q_after,
    )

    assert layout_before["batch_capacity"] == batch_capacity
    assert layout_before["batch_count"] == 1
    assert layout_after["batch_capacity"] == batch_capacity
    assert layout_after["batch_count"] == 2

    labor_before = ep.calculate_electroplating_labor_hours(
        operation_time_min=60.0,
        batch_quantity=layout_before["batch_quantity"],
        workers_count=1,
        requested_quantity=layout_before["requested_quantity"],
        batch_count=layout_before["batch_count"],
    )
    labor_after = ep.calculate_electroplating_labor_hours(
        operation_time_min=60.0,
        batch_quantity=layout_after["batch_quantity"],
        workers_count=1,
        requested_quantity=layout_after["requested_quantity"],
        batch_count=layout_after["batch_count"],
    )

    order_labor_before = labor_before["labor_time_min"] * q_before
    order_labor_after = labor_after["labor_time_min"] * q_after

    assert labor_before["labor_formula_effective_n"] == pytest.approx(float(batch_capacity))
    assert labor_after["labor_formula_effective_n"] == pytest.approx(float(batch_capacity))
    assert order_labor_before == pytest.approx(ELECTROPLATING_LABOR_TIME_COEF * 60.0)
    assert order_labor_after == pytest.approx((q_after / batch_capacity) * ELECTROPLATING_LABOR_TIME_COEF * 60.0)
    assert order_labor_after / order_labor_before == pytest.approx(q_after / q_before)
