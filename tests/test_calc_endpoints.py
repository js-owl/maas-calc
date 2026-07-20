def test_calculate_printing_ok(client):
    payload = {
        "service_id": "printing",
        "file_id": "test-printing-123",
        "dimensions": {
            "length": 100,
            "width": 50,
            "height": 10
        },
        "quantity": 2,
        "material_id": "plastic_ABS",
        "material_form": "thread",
        "cover_id": ["1"],
        "k_cert": ["a"]
    }
    r = client.post("/calculate-price", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == True
    assert "data" in data
    assert "detail_price" in data["data"]


def test_calculate_cnc_milling_without_file_data_returns_error(client):
    payload = {
        "service_id": "cnc-milling",
        "file_id": "test-cnc-milling-456",
        "dimensions": {"length": 100, "width": 50, "height": 10},
        "quantity": 1,
        "material_id": "non_ferrous_Д16",
        "material_form": "sheet",
        "tolerance_id": "1",
        "finish_id": "1",
        "cover_id": ["1"],
        "k_cert": ["a"]
    }
    r = client.post("/calculate-price", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert "file_data is required" in data.get("error", "")




def test_other_service_returns_successful_zero_manual_price(client):
    payload = {"service_id": "bending", "file_id": "manual-bending-001"}
    r = client.post("/calculate-price", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["calculation_method"] == "manual_pricing"
    assert data["data"]["total_price"] == 0
