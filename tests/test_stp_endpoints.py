# STP endpoints were removed during refactoring - all tests disabled
# This file is kept for reference but all tests are commented out

# import io
# import pytest
# from fastapi.testclient import TestClient
# from main import app

# client = TestClient(app)

# def test_stp_dimensions_invalid_file_type(client):
#     """Test STP dimensions endpoint with invalid file type"""
#     # Create a dummy text file
#     dummy_content = b"This is not an STP file"
#     files = {"file": ("test.txt", io.BytesIO(dummy_content), "text/plain")}
#     
#     response = client.post("/calculate-stp-dimensions/", files=files)
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" in data["error"]


# def test_stp_volume_invalid_file_type(client):
#     """Test STP volume endpoint with invalid file type"""
#     # Create a dummy text file
#     dummy_content = b"This is not an STP file"
#     files = {"file": ("test.txt", io.BytesIO(dummy_content), "text/plain")}
#     
#     response = client.post("/calculate-stp-volume/", files=files)
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" in data["error"]


# def test_stp_assembly_invalid_file_type(client):
#     """Test STP assembly endpoint with invalid file type"""
#     # Create a dummy text file
#     dummy_content = b"This is not an STP file"
#     files = {"file": ("test.txt", io.BytesIO(dummy_content), "text/plain")}
#     
#     response = client.post("/analyze-stp-assembly/", files=files)
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" in data["error"]


# def test_stp_dimensions_valid_stp_extension(client):
#     """Test STP dimensions endpoint with valid .stp extension"""
#     # Create a dummy STP file (this will fail processing but should pass file type validation)
#     dummy_content = b"# This is a dummy STP file content"
#     files = {"file": ("test.stp", io.BytesIO(dummy_content), "application/step")}
#     
#     response = client.post("/calculate-stp-dimensions/", files=files)
#     # Should fail processing but not file type validation
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" not in data["error"]


# def test_stp_dimensions_valid_step_extension(client):
#     """Test STP dimensions endpoint with valid .step extension"""
#     # Create a dummy STEP file (this will fail processing but should pass file type validation)
#     dummy_content = b"# This is a dummy STEP file content"
#     files = {"file": ("test.step", io.BytesIO(dummy_content), "application/step")}
#     
#     response = client.post("/calculate-stp-dimensions/", files=files)
#     # Should fail processing but not file type validation
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" not in data["error"]


# def test_stp_volume_valid_stp_extension(client):
#     """Test STP volume endpoint with valid .stp extension"""
#     # Create a dummy STP file (this will fail processing but should pass file type validation)
#     dummy_content = b"# This is a dummy STP file content"
#     files = {"file": ("test.stp", io.BytesIO(dummy_content), "application/step")}
#     
#     response = client.post("/calculate-stp-volume/", files=files)
#     # Should fail processing but not file type validation
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" not in data["error"]


# def test_stp_assembly_valid_stp_extension(client):
#     """Test STP assembly endpoint with valid .stp extension"""
#     # Create a dummy STP file (this will fail processing but should pass file type validation)
#     dummy_content = b"# This is a dummy STP file content"
#     files = {"file": ("test.stp", io.BytesIO(dummy_content), "application/step")}
#     
#     response = client.post("/analyze-stp-assembly/", files=files)
#     # Should fail processing but not file type validation
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" not in data["error"]


# def test_stp_endpoints_case_insensitive_extension(client):
#     """Test that STP endpoints accept case-insensitive file extensions"""
#     # Test .STP (uppercase)
#     dummy_content = b"# This is a dummy STP file content"
#     files = {"file": ("test.STP", io.BytesIO(dummy_content), "application/step")}
#     
#     response = client.post("/calculate-stp-dimensions/", files=files)
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data
#     assert "Invalid file type" not in data["error"]


# def test_stp_endpoints_missing_file(client):
#     """Test STP endpoints with missing file parameter"""
#     response = client.post("/calculate-stp-dimensions/")
#     assert response.status_code == 422  # Validation error for missing file


# def test_stp_endpoints_empty_file(client):
#     """Test STP endpoints with empty file"""
#     empty_content = b""
#     files = {"file": ("empty.stp", io.BytesIO(empty_content), "application/step")}
#     
#     response = client.post("/calculate-stp-dimensions/", files=files)
#     assert response.status_code == 400
#     data = response.json()
#     assert "error" in data


# def test_stp_processing_functions():
#     """Test STP processing functions directly"""
#     from main import process_stp_file, analyze_stp_assembly
#     
#     # Test with dummy content
#     dummy_content = b"# This is a dummy STP file content"
#     
#     # These should raise exceptions for invalid content
#     with pytest.raises(Exception):
#         process_stp_file(dummy_content)
#     
#     with pytest.raises(Exception):
#         analyze_stp_assembly(dummy_content)


# def test_stp_response_models():
#     """Test STP response model validation"""
#     from main import STPFileInfo, STPDimensionsResponse, STPVolumeResponse, STPAssemblyResponse, STPAssemblyInfo
#     
#     # Test STPFileInfo
#     file_info = STPFileInfo(
#         filename="test.stp",
#         file_size=1024,
#         file_type="stp"
#     )
#     assert file_info.filename == "test.stp"
#     assert file_info.file_size == 1024
#     assert file_info.file_type == "stp"
#     
#     # Test STPDimensionsResponse
#     dimensions_response = STPDimensionsResponse(
#         dimensions={"length": 100.0, "width": 50.0, "height": 25.0},
#         bounding_box={"min": [0, 0, 0], "max": [100, 50, 25]},
#         file_info=file_info
#     )
#     assert dimensions_response.dimensions["length"] == 100.0
#     assert len(dimensions_response.bounding_box["min"]) == 3
#     
#     # Test STPVolumeResponse
#     volume_response = STPVolumeResponse(
#         volume=125000.0,
#         file_info=file_info
#     )
#     assert volume_response.volume == 125000.0
#     
#     # Test STPAssemblyInfo
#     assembly_info = STPAssemblyInfo(
#         part_name="TestPart",
#         part_id="PART001",
#         material="Steel",
#         volume=50000.0,
#         dimensions={"length": 50.0, "width": 25.0, "height": 40.0}
#     )
#     assert assembly_info.part_name == "TestPart"
#     assert assembly_info.part_id == "PART001"
#     
#     # Test STPAssemblyResponse
#     assembly_response = STPAssemblyResponse(
#         assembly_name="TestAssembly",
#         total_parts=1,
#         total_volume=50000.0,
#         parts=[assembly_info],
#         file_info=file_info
#     )
#     assert assembly_response.assembly_name == "TestAssembly"
#     assert assembly_response.total_parts == 1
#     assert len(assembly_response.parts) == 1