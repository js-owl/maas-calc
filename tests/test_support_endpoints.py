def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == True
    assert "data" in data
    assert data["data"]["status"] == "healthy"


def test_materials_list(client):
    r = client.get("/materials")
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == True
    assert "data" in data
    assert "materials" in data["data"]
    arr = data["data"]["materials"]
    assert isinstance(arr, list)
    assert any(item["id"].startswith("alum_") for item in arr)


def test_materials_filter_by_process(client):
    r = client.get("/materials", params={"process": "printing"})
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == True
    assert "data" in data
    assert "materials" in data["data"]
    arr = data["data"]["materials"]
    # metals should be filtered out for printing
    assert all(item["family"] in ("plastic",) for item in arr)


def test_options_coefficients(client):
    r = client.get("/coefficients")
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == True
    assert "data" in data
    assert "tolerance" in data["data"] and isinstance(data["data"]["tolerance"], list)
    assert "finish" in data["data"] and isinstance(data["data"]["finish"], list)
    assert "cover" in data["data"] and isinstance(data["data"]["cover"], list)


def test_services(client):
    r = client.get("/services")
    assert r.status_code == 200
    data = r.json()
    assert "success" in data
    assert data["success"] == True
    assert "data" in data
    assert "services" in data["data"]
    services = data["data"]["services"]
    assert isinstance(services, list)
    # Check that we have some expected service IDs (using actual names from the endpoint)
    assert "printing" in services
    assert "cnc-milling" in services
    #assert "cnc-lathe" in services
    #assert "painting" in services
    assert "bending" in services


