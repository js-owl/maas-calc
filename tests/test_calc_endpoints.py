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
        "material_id": "PA11",
        "material_form": "powder",
        "k_type": 1.0,
        "k_process": 1.0,
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


def test_calculate_cnc_milling_ok(client):
    payload = {
        "service_id": "cnc-milling",
        "file_id": "test-cnc-milling-456",
        "dimensions": {
            "length": 100,
            "width": 50,
            "height": 10
        },
        "quantity": 1,
        "material_id": "alum_D16",
        "material_form": "sheet",
        "tolerance_id": "1",
        "finish_id": "1",
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


def test_calculate_cnc_lathe_ok(client):
    payload = {
        "service_id": "cnc-lathe",
        "file_id": "test-cnc-lathe-789",
        "dimensions": {
            "length": 100,
            "width": 20,
            "height": 20
        },
        "quantity": 1,
        "material_id": "steel_12X18H10T",
        "material_form": "rod",
        "tolerance_id": "1",
        "finish_id": "1",
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


def test_calculate_painting_ok(client):
    payload = {
        "service_id": "painting",
        "file_id": "test-painting-101",
        "dimensions": {
            "length": 100,
            "width": 50,
            "height": 10
        },
        "quantity": 1,
        "material_id": "alum_D16",
        "material_form": "sheet",
        "paint_type": "epoxy",
        "paint_color": "RAL1018",
        "control_type": "1",
        "k_cert": ["a"]
    }
    r = client.post("/calculate-price", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == True
    assert "data" in data
    assert "detail_price" in data["data"]


