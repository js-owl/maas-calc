"""
API Testing Examples for Manufacturing Calculations API

This file contains comprehensive examples for testing all endpoints
with various scenarios including valid requests, edge cases, and error conditions.
"""

import requests
import json
import base64
import sys
import os
from typing import Dict, Any

# Add parent directory to path to import constants
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import APP_VERSION

# API Configuration
BASE_URL = "http://localhost:7000"
API_ENDPOINT = f"{BASE_URL}/calculate-price"

# Test data for different manufacturing services
# Using real material IDs, tolerance IDs, finish IDs, and cover IDs from constants.py
TEST_DATA = {
    "printing": {
        "service_id": "printing",
        "file_id": "test-printing-001",
        "dimensions": {
            "length": 100.0,
            "width": 50.0,
            "thickness": 10.0
        },
        "quantity": 5,
        "material_id": "PA11",  # Порошок PA11 - real from constants
        "material_form": "powder",
        "n_dimensions": 1,
        "k_type": 1.0,
        "k_process": 1.0,
        "cover_id": ["1"],  # Покраска - real from constants
        "k_otk": 1.0,
        "k_cert": ["a", "f"]
    },
    
    "cnc_milling": {
        "service_id": "cnc-milling",
        "file_id": "test-cnc-milling-001",
        "dimensions": {
            "length": 80.0,
            "width": 60.0,
            "thickness": 15.0
        },
        "quantity": 10,
        "material_id": "alum_D16",  # Алюминий Д16 - real from constants
        "material_form": "sheet",
        "tolerance_id": "1",  # IT7 - real from constants
        "finish_id": "1",     # 12.5 - real from constants
        "cover_id": ["1"],    # Покраска - real from constants
        "k_otk": 1.0,
        "cnc_complexity": "medium",
        "cnc_setup_time": 2.0
    },
    
    "cnc_lathe": {
        "service_id": "cnc-lathe",
        "file_id": "test-cnc-lathe-001",
        "dimensions": {
            "length": 120.0,
            "width": 25.0,  # diameter for lathe
            "thickness": 25.0
        },
        "quantity": 8,
        "material_id": "alum_AMC",  # Алюминий АМц - real from constants
        "material_form": "rod",
        "tolerance_id": "2",  # IT8 - real from constants
        "finish_id": "3",     # 3.2 - real from constants
        "cover_id": ["2"],    # Гальваника - real from constants
        "k_otk": 1.0,
        "cnc_complexity": "high",
        "cnc_setup_time": 3.0
    },
    
    "painting": {
        "service_id": "painting",
        "file_id": "test-painting-001",
        "dimensions": {
            "length": 100.0,
            "width": 80.0,
            "thickness": 5.0
        },
        "quantity": 15,
        "material_id": "alum_D16",  # Алюминий Д16 - real from constants
        "material_form": "sheet",
        "paint_type": "acrylic",    # real from PAINT_COEFFICIENTS
        "paint_prepare": "a",       # real from PROCESS_COEFFICIENTS
        "paint_primer": "b",        # real from PROCESS_COEFFICIENTS
        "paint_lakery": "a",        # real from PROCESS_COEFFICIENTS
        "control_type": "1",
        "k_cert": ["a", "f", "g"]
    }
}

# Edge cases and error scenarios using real constants
EDGE_CASES = {
    "minimal_parameters": {
        "service_id": "printing",
        "file_id": "minimal-test",
        "dimensions": {"length": 1.0, "width": 1.0, "thickness": 1.0},
        "quantity": 1
    },
    
    "large_quantity": {
        "service_id": "cnc-milling",
        "file_id": "large-qty-test",
        "dimensions": {"length": 50.0, "width": 50.0, "thickness": 10.0},
        "quantity": 1000,
        "material_id": "alum_D16",  # Real material
        "material_form": "sheet"
    },
    
    "multiple_cover_types": {
        "service_id": "printing",
        "file_id": "multi-cover-test",
        "dimensions": {"length": 50.0, "width": 50.0, "thickness": 5.0},
        "quantity": 3,
        "material_id": "PA12",  # Different plastic material
        "material_form": "powder",
        "cover_id": ["1", "2"]  # Покраска + Гальваника - real from constants
    },
    
    "high_complexity_cnc": {
        "service_id": "cnc-milling",
        "file_id": "complex-cnc-test",
        "dimensions": {"length": 200.0, "width": 150.0, "thickness": 50.0},
        "quantity": 2,
        "material_id": "alum_D16",  # Real material
        "material_form": "sheet",
        "cnc_complexity": "high",
        "cnc_setup_time": 5.0,
        "tolerance_id": "1",  # IT7 - real from constants
        "finish_id": "5"      # 0.8 - real from constants
    },
    
    "different_tolerance_levels": {
        "service_id": "cnc-lathe",
        "file_id": "tolerance-test",
        "dimensions": {"length": 80.0, "width": 30.0, "thickness": 30.0},
        "quantity": 5,
        "material_id": "alum_AMC",  # Real material
        "material_form": "rod",
        "tolerance_id": "5",  # IT11 - real from constants
        "finish_id": "4",     # 1.6 - real from constants
        "cover_id": ["1"]     # Покраска - real from constants
    },
    
    "different_paint_types": {
        "service_id": "painting",
        "file_id": "paint-test",
        "dimensions": {"length": 60.0, "width": 40.0, "thickness": 3.0},
        "quantity": 20,
        "material_id": "alum_D16",  # Real material
        "material_form": "sheet",
        "paint_type": "epoxy",      # Real from PAINT_COEFFICIENTS
        "paint_prepare": "c",       # Real from PROCESS_COEFFICIENTS
        "paint_primer": "c",        # Real from PROCESS_COEFFICIENTS
        "paint_lakery": "b"         # Real from PROCESS_COEFFICIENTS
    }
}

# Invalid data for error testing
INVALID_CASES = {
    "invalid_service": {
        "service_id": "invalid-service",
        "file_id": "error-test-001",
        "dimensions": {"length": 10.0, "width": 10.0, "thickness": 10.0},
        "quantity": 1
    },
    
    "invalid_material": {
        "service_id": "printing",
        "file_id": "error-test-002",
        "dimensions": {"length": 10.0, "width": 10.0, "thickness": 10.0},
        "quantity": 1,
        "material_id": "invalid_material",
        "material_form": "powder"
    },
    
    "invalid_dimensions": {
        "service_id": "printing",
        "file_id": "error-test-003",
        "dimensions": {"length": -10.0, "width": 0.0, "thickness": 10.0},
        "quantity": 1
    },
    
    "missing_required_fields": {
        "service_id": "printing",
        "file_id": "error-test-004"
        # Missing dimensions and quantity
    }
}

def test_endpoint(endpoint: str, data: Dict[str, Any], description: str) -> None:
    """Test a single endpoint with given data"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    print(f"Endpoint: {endpoint}")
    print(f"Request Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(endpoint, json=data, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS")
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print("❌ ERROR")
            print(f"Error Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")

def test_health_endpoint() -> None:
    """Test the health check endpoint"""
    print(f"\n{'='*60}")
    print("TEST: Health Check")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")

def test_materials_endpoint() -> None:
    """Test the materials listing endpoint"""
    print(f"\n{'='*60}")
    print("TEST: Materials List")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/materials", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            materials = response.json()
            print(f"Total Materials: {len(materials.get('materials', []))}")
            print("Sample Materials:")
            for material in materials.get('materials', [])[:3]:
                print(f"  - {material.get('id')}: {material.get('label')}")
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")

def test_services_endpoint() -> None:
    """Test the services listing endpoint"""
    print(f"\n{'='*60}")
    print("TEST: Services List")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/services", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Available Services: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")

def test_coefficients_endpoint() -> None:
    """Test the coefficients listing endpoint"""
    print(f"\n{'='*60}")
    print("TEST: Coefficients List")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/coefficients", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            coeffs = response.json()
            print("Available Coefficients:")
            for key, values in coeffs.items():
                print(f"  {key}: {len(values)} options")
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")

def run_all_tests() -> None:
    """Run all test examples"""
    print(f"🚀 Starting Manufacturing Calculations API v{APP_VERSION} Test Suite")
    print(f"Testing against: {BASE_URL}")
    
    # Test basic endpoints
    test_health_endpoint()
    test_services_endpoint()
    test_materials_endpoint()
    test_coefficients_endpoint()
    
    # Test valid manufacturing calculations
    print(f"\n{'='*80}")
    print("MANUFACTURING CALCULATION TESTS")
    print(f"{'='*80}")
    
    for service, data in TEST_DATA.items():
        test_endpoint(API_ENDPOINT, data, f"Valid {service.replace('_', ' ').title()} Calculation")
    
    # Test edge cases
    print(f"\n{'='*80}")
    print("EDGE CASE TESTS")
    print(f"{'='*80}")
    
    for case_name, data in EDGE_CASES.items():
        test_endpoint(API_ENDPOINT, data, f"Edge Case: {case_name.replace('_', ' ').title()}")
    
    # Test error cases
    print(f"\n{'='*80}")
    print("ERROR CASE TESTS")
    print(f"{'='*80}")
    
    for case_name, data in INVALID_CASES.items():
        test_endpoint(API_ENDPOINT, data, f"Error Case: {case_name.replace('_', ' ').title()}")
    
    # Test comprehensive scenarios with real constants
    test_comprehensive_materials()
    test_all_tolerance_finish_combinations()
    test_all_cover_types()
    test_all_paint_types()
    
    print(f"\n{'='*80}")
    print("✅ Test Suite Complete")
    print(f"{'='*80}")

def test_comprehensive_materials() -> None:
    """Test with various real materials from constants.py"""
    print(f"\n{'='*60}")
    print("TEST: Comprehensive Material Testing")
    print(f"{'='*60}")
    
    # Test different materials for each service
    material_tests = [
        {
            "service_id": "printing",
            "file_id": "material-test-pa11",
            "dimensions": {"length": 50.0, "width": 30.0, "thickness": 8.0},
            "quantity": 3,
            "material_id": "PA11",
            "material_form": "powder"
        },
        {
            "service_id": "printing", 
            "file_id": "material-test-pa12",
            "dimensions": {"length": 40.0, "width": 25.0, "thickness": 6.0},
            "quantity": 2,
            "material_id": "PA12",
            "material_form": "powder"
        },
        {
            "service_id": "cnc-milling",
            "file_id": "material-test-alum-d16",
            "dimensions": {"length": 70.0, "width": 45.0, "thickness": 12.0},
            "quantity": 4,
            "material_id": "alum_D16",
            "material_form": "sheet",
            "tolerance_id": "1",
            "finish_id": "1"
        },
        {
            "service_id": "cnc-milling",
            "file_id": "material-test-alum-amc",
            "dimensions": {"length": 60.0, "width": 35.0, "thickness": 10.0},
            "quantity": 6,
            "material_id": "alum_AMC",
            "material_form": "sheet",
            "tolerance_id": "2",
            "finish_id": "2"
        }
    ]
    
    for test in material_tests:
        test_endpoint(API_ENDPOINT, test, f"Material Test: {test['material_id']}")

def test_all_tolerance_finish_combinations() -> None:
    """Test different tolerance and finish combinations"""
    print(f"\n{'='*60}")
    print("TEST: Tolerance and Finish Combinations")
    print(f"{'='*60}")
    
    # Test different tolerance/finish combinations
    combinations = [
        {"tolerance_id": "1", "finish_id": "1", "description": "IT7 + 12.5"},
        {"tolerance_id": "3", "finish_id": "3", "description": "IT9 + 3.2"},
        {"tolerance_id": "5", "finish_id": "5", "description": "IT11 + 0.8"},
    ]
    
    for i, combo in enumerate(combinations):
        test_data = {
            "service_id": "cnc-milling",
            "file_id": f"tolerance-finish-test-{i+1}",
            "dimensions": {"length": 50.0, "width": 30.0, "thickness": 8.0},
            "quantity": 2,
            "material_id": "alum_D16",
            "material_form": "sheet",
            "tolerance_id": combo["tolerance_id"],
            "finish_id": combo["finish_id"],
            "cover_id": ["1"]
        }
        test_endpoint(API_ENDPOINT, test_data, f"Tolerance/Finish: {combo['description']}")

def test_all_cover_types() -> None:
    """Test different cover processing types"""
    print(f"\n{'='*60}")
    print("TEST: Cover Processing Types")
    print(f"{'='*60}")
    
    # Test different cover types
    cover_tests = [
        {"cover_id": ["1"], "description": "Покраска only"},
        {"cover_id": ["2"], "description": "Гальваника only"},
        {"cover_id": ["1", "2"], "description": "Покраска + Гальваника"},
        {"cover_id": [], "description": "No cover processing"}
    ]
    
    for i, cover_test in enumerate(cover_tests):
        test_data = {
            "service_id": "printing",
            "file_id": f"cover-test-{i+1}",
            "dimensions": {"length": 30.0, "width": 20.0, "thickness": 5.0},
            "quantity": 1,
            "material_id": "PA11",
            "material_form": "powder",
            "cover_id": cover_test["cover_id"]
        }
        test_endpoint(API_ENDPOINT, test_data, f"Cover Test: {cover_test['description']}")

def test_all_paint_types() -> None:
    """Test different paint types and process combinations"""
    print(f"\n{'='*60}")
    print("TEST: Paint Types and Process Combinations")
    print(f"{'='*60}")
    
    # Test different paint types from PAINT_COEFFICIENTS
    paint_tests = [
        {
            "paint_type": "acrylic",
            "paint_prepare": "a",
            "paint_primer": "a", 
            "paint_lakery": "a",
            "description": "Acrylic - Basic Process"
        },
        {
            "paint_type": "epoxy",
            "paint_prepare": "b",
            "paint_primer": "b",
            "paint_lakery": "b", 
            "description": "Epoxy - Enhanced Process"
        },
        {
            "paint_type": "polyurethane",
            "paint_prepare": "c",
            "paint_primer": "c",
            "paint_lakery": "c",
            "description": "Polyurethane - Premium Process"
        }
    ]
    
    for i, paint_test in enumerate(paint_tests):
        test_data = {
            "service_id": "painting",
            "file_id": f"paint-test-{i+1}",
            "dimensions": {"length": 40.0, "width": 30.0, "thickness": 4.0},
            "quantity": 5,
            "material_id": "alum_D16",
            "material_form": "sheet",
            "paint_type": paint_test["paint_type"],
            "paint_prepare": paint_test["paint_prepare"],
            "paint_primer": paint_test["paint_primer"],
            "paint_lakery": paint_test["paint_lakery"],
            "control_type": "1"
        }
        test_endpoint(API_ENDPOINT, test_data, f"Paint Test: {paint_test['description']}")

def test_with_file_upload() -> None:
    """Test with file upload (requires actual STL/STP file)"""
    print(f"\n{'='*60}")
    print("TEST: File Upload (STL/STP)")
    print(f"{'='*60}")
    
    # Example with base64 encoded file (you would replace with actual file)
    sample_stl_data = base64.b64encode(b"dummy stl content").decode('utf-8')
    
    file_data = {
        "service_id": "printing",
        "file_id": "file-upload-test",
        "file_data": sample_stl_data,
        "file_name": "test.stl",
        "file_type": "stl",
        "quantity": 1
    }
    
    test_endpoint(API_ENDPOINT, file_data, "File Upload Test")

if __name__ == "__main__":
    # Run all tests
    run_all_tests()
    
    # Uncomment to test file upload
    # test_with_file_upload()
