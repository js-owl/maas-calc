def test_invalid_material_for_printing(client):
    payload = {
        "service_id": "printing",
        "file_id": "test-invalid-printing-123",
        "dimensions": {
            "length": 100,
            "width": 50,
            "height": 10
        },
        "quantity": 1,
        "material_id": "alum_D16",
        "material_form": "sheet",
        "k_type": 1.0,
        "k_process": 1.0,
        "cover_id": ["1"],
        "k_cert": ["a"]
    }
    r = client.post("/calculate-price", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == False
    assert "error" in data


def test_lathe_requires_rod_bar_tube(client):
    payload = {
        "service_id": "cnc-lathe",
        "file_id": "test-invalid-lathe-456",
        "dimensions": {
            "length": 100,
            "width": 20,
            "height": 20
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
    assert data["success"] == False
    assert "error" in data


