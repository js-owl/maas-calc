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
        "material_id": "non_ferrous_Д16",
        "material_form": "sheet",
        "cover_id": ["1"],
        "k_cert": ["a"]
    }
    r = client.post("/calculate-price", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == False
    assert "error" in data


