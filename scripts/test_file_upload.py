#!/usr/bin/env python3
"""
Test script for file upload functionality with the unified endpoint
"""

import requests
import json
import sys
from pathlib import Path
import os

# Add the parent directory to the path so we can import from main
sys.path.append(str(Path(__file__).parent.parent))

def create_test_stl_file():
    """Create a simple test STL file for testing"""
    # This is a minimal STL file content (binary)
    stl_content = b"""solid test_cube
  facet normal 0.0 0.0 1.0
    outer loop
      vertex 0.0 0.0 0.0
      vertex 10.0 0.0 0.0
      vertex 10.0 10.0 0.0
    endloop
  endfacet
  facet normal 0.0 0.0 1.0
    outer loop
      vertex 0.0 0.0 0.0
      vertex 10.0 10.0 0.0
      vertex 0.0 10.0 0.0
    endloop
  endfacet
  facet normal 0.0 0.0 -1.0
    outer loop
      vertex 0.0 0.0 5.0
      vertex 0.0 10.0 5.0
      vertex 10.0 10.0 5.0
    endloop
  endfacet
  facet normal 0.0 0.0 -1.0
    outer loop
      vertex 0.0 0.0 5.0
      vertex 10.0 10.0 5.0
      vertex 10.0 0.0 5.0
    endloop
  endfacet
  facet normal 0.0 1.0 0.0
    outer loop
      vertex 0.0 10.0 0.0
      vertex 10.0 10.0 0.0
      vertex 10.0 10.0 5.0
    endloop
  endfacet
  facet normal 0.0 1.0 0.0
    outer loop
      vertex 0.0 10.0 0.0
      vertex 10.0 10.0 5.0
      vertex 0.0 10.0 5.0
    endloop
  endfacet
  facet normal 0.0 -1.0 0.0
    outer loop
      vertex 0.0 0.0 0.0
      vertex 0.0 0.0 5.0
      vertex 10.0 0.0 5.0
    endloop
  endfacet
  facet normal 0.0 -1.0 0.0
    outer loop
      vertex 0.0 0.0 0.0
      vertex 10.0 0.0 5.0
      vertex 10.0 0.0 0.0
    endloop
  endfacet
  facet normal 1.0 0.0 0.0
    outer loop
      vertex 10.0 0.0 0.0
      vertex 10.0 0.0 5.0
      vertex 10.0 10.0 5.0
    endloop
  endfacet
  facet normal 1.0 0.0 0.0
    outer loop
      vertex 10.0 0.0 0.0
      vertex 10.0 10.0 5.0
      vertex 10.0 10.0 0.0
    endloop
  endfacet
  facet normal -1.0 0.0 0.0
    outer loop
      vertex 0.0 0.0 0.0
      vertex 0.0 10.0 0.0
      vertex 0.0 10.0 5.0
    endloop
  endfacet
  facet normal -1.0 0.0 0.0
    outer loop
      vertex 0.0 0.0 0.0
      vertex 0.0 10.0 5.0
      vertex 0.0 0.0 5.0
    endloop
  endfacet
endsolid test_cube"""
    
    test_file_path = Path(__file__).parent / "test_cube.stl"
    with open(test_file_path, "wb") as f:
        f.write(stl_content)
    
    return test_file_path

def test_file_upload_with_3d_printing():
    """Test file upload with 3D printing service using base64"""
    print("Testing file upload with 3D printing using base64...")
    
    # Create test STL file
    test_file_path = create_test_stl_file()
    
    try:
        import base64
        
        # Read file and encode as base64
        with open(test_file_path, 'rb') as f:
            file_bytes = f.read()
            file_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Prepare the JSON request
        payload = {
            'service_id': 'printing',
            'file_id': 'test-stl-upload-123',
            'file_data': file_data,
            'file_name': 'test_cube.stl',
            'file_type': 'stl',
            'quantity': 3,
            'material_id': 'PA11',
            'material_form': 'powder',
            'n_dimensions': 1,
            'k_type': 1.0,
            'k_process': 1.0,
            'cover_id': ['1'],
            'k_cert': []
        }
        
        response = requests.post('http://localhost:7000/calculate-price', json=payload)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print('Success!')
            print(f'Service ID: {result.get("service_id")}')
            print(f'File ID: {result.get("file_id")}')
            print(f'Filename: {result.get("filename")}')
            print(f'Detail Price: {result.get("detail_price")}')
            print(f'Total Price: {result.get("total_price")}')
            print(f'Extracted Dimensions: {result.get("extracted_dimensions")}')
            return True
        else:
            print('❌ Error:', response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print('❌ Connection error: Server not running on localhost:7000')
        return False
    except Exception as e:
        print(f'Error: {e}')
        return False
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()

def test_file_upload_with_cnc_milling():
    """Test file upload with CNC milling service using base64"""
    print("\nTesting file upload with CNC milling using base64...")
    
    # Create test STL file
    test_file_path = create_test_stl_file()
    
    try:
        import base64
        
        # Read file and encode as base64
        with open(test_file_path, 'rb') as f:
            file_bytes = f.read()
            file_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Prepare the JSON request
        payload = {
            'service_id': 'cnc-milling',
            'file_id': 'test-cnc-upload-456',
            'file_data': file_data,
            'file_name': 'test_cube.stl',
            'file_type': 'stl',
            'quantity': 5,
            'material_id': 'alum_D16',
            'material_form': 'sheet',
            'cover_id': ['1'],
            'k_cert': ['a']
        }
        
        response = requests.post('http://localhost:7000/calculate-price', json=payload)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print('Success!')
            print(f'Service ID: {result.get("service_id")}')
            print(f'File ID: {result.get("file_id")}')
            print(f'Filename: {result.get("filename")}')
            print(f'Detail Price: {result.get("detail_price")}')
            print(f'Total Price: {result.get("total_price")}')
            print(f'Extracted Dimensions: {result.get("extracted_dimensions")}')
            return True
        else:
            print('❌ Error:', response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print('❌ Connection error: Server not running on localhost:7000')
        return False
    except Exception as e:
        print(f'Error: {e}')
        return False
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()

def main():
    """Run all file upload tests"""
    print("Testing File Upload with Unified Endpoint")
    print("=" * 50)
    
    tests = [
        test_file_upload_with_3d_printing,
        test_file_upload_with_cnc_milling
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
        print("All file upload tests passed!")
        return 0
    else:
        print("Some file upload tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
