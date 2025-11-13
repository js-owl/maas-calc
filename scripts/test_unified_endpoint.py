#!/usr/bin/env python3
"""
Test script for the unified /calculate-price endpoint
"""

import requests
import json
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from main
sys.path.append(str(Path(__file__).parent.parent))

def test_unified_endpoint_without_file():
    """Test the unified endpoint without file upload"""
    print("Testing unified endpoint without file upload...")
    
    payload = {
        'service_id': 'printing',
        'file_id': 'test-file-123',
        'quantity': 5,
        'dimensions': {
            'length': 100.0,
            'width': 50.0,
            'thickness': 10.0
        },
        'material_id': 'PA11',
        'material_form': 'powder',
        'n_dimensions': 1,
        'k_type': 1.0,
        'k_process': 1.0,
        'cover_id': ['1'],
        'k_cert': []
    }
    
    try:
        response = requests.post('http://localhost:7000/calculate-price', json=payload)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print('Success!')
            print(f'Service ID: {data.get("service_id")}')
            print(f'File ID: {data.get("file_id")}')
            print(f'Detail Price: {data.get("detail_price")}')
            print(f'Total Price: {data.get("total_price")}')
            print(f'Calculation Method: {data.get("calculation_method")}')
            print(f'Timestamp: {data.get("timestamp")}')
            return True
        else:
            print('Error:', response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print('❌ Connection error: Server not running on localhost:7000')
        return False
    except Exception as e:
        print(f'Error: {e}')
        return False

def test_unified_endpoint_cnc_milling():
    """Test the unified endpoint for CNC milling"""
    print("\nTesting unified endpoint for CNC milling...")
    
    payload = {
        'service_id': 'cnc-milling',
        'file_id': 'test-cnc-file-456',
        'quantity': 10,
        'dimensions': {
            'length': 200.0,
            'width': 100.0,
            'thickness': 25.0
        },
        'material_id': 'alum_D16',
        'material_form': 'sheet',
        'cover_id': ['1', '2'],
        'k_cert': ['a', 'f']
    }
    
    try:
        response = requests.post('http://localhost:7000/calculate-price', json=payload)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print('Success!')
            print(f'Service ID: {data.get("service_id")}')
            print(f'File ID: {data.get("file_id")}')
            print(f'Detail Price: {data.get("detail_price")}')
            print(f'Total Price: {data.get("total_price")}')
            print(f'Manufacturing Cycle: {data.get("manufacturing_cycle")} days')
            return True
        else:
            print('Error:', response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print('❌ Connection error: Server not running on localhost:7000')
        return False
    except Exception as e:
        print(f'Error: {e}')
        return False

def test_unified_endpoint_with_safeguards():
    """Test the unified endpoint with minimal parameters (testing safeguards)"""
    print("\nTesting unified endpoint with safeguards...")
    
    payload = {
        'service_id': 'printing',
        'file_id': 'test-safeguards-789'
        # No other parameters - should use defaults
    }
    
    try:
        response = requests.post('http://localhost:7000/calculate-price', json=payload)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print('Success!')
            print(f'Service ID: {data.get("service_id")}')
            print(f'File ID: {data.get("file_id")}')
            print(f'Detail Price: {data.get("detail_price")}')
            print(f'Used Parameters: {data.get("used_parameters")}')
            print('Safeguards working - used default values')
            return True
        else:
            print('Error:', response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print('❌ Connection error: Server not running on localhost:7000')
        return False
    except Exception as e:
        print(f'Error: {e}')
        return False

def main():
    """Run all tests"""
    print("Testing Unified /calculate-price Endpoint")
    print("=" * 50)
    
    tests = [
        test_unified_endpoint_without_file,
        test_unified_endpoint_cnc_milling,
        test_unified_endpoint_with_safeguards
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
