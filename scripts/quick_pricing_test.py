#!/usr/bin/env python3
"""
Quick Pricing Test - Simplified version for rapid testing
Tests key quantities across both file types and calculation methods
"""

import requests
import json
import base64
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:7000"
API_ENDPOINT = f"{BASE_URL}/calculate-price"

def quick_test():
    """Quick test of key scenarios"""
    print("🚀 Quick Pricing Test")
    print("=" * 50)
    
    # Load test files
    test_files = {
        "stl": "test_files/02.stl",
        "stp": "test_files/S8000_125_63_293_001_D000_02.stp"
    }
    
    file_data = {}
    for file_type, file_path in test_files.items():
        path = Path(file_path)
        if path.exists():
            with open(path, 'rb') as f:
                file_data[file_type] = base64.b64encode(f.read()).decode('utf-8')
            print(f"✅ Loaded {file_type.upper()}: {path.name}")
        else:
            print(f"❌ Missing {file_type.upper()}: {file_path}")
    
    # Test scenarios: (quantity, expected_k_quantity, description)
    test_scenarios = [
        (1, 1.0, "Single unit"),
        (25, 0.95, "5% discount"),
        (150, 0.85, "15% discount"),
        (600, 0.8, "20% discount")
    ]
    
    print(f"\n📊 Testing {len(test_scenarios)} scenarios × 2 file types × 2 methods = {len(test_scenarios) * 2 * 2} total tests")
    print("-" * 50)
    
    results = []
    
    for file_type in file_data.keys():
        print(f"\n📁 {file_type.upper()} Files:")
        
        for quantity, expected_k_quantity, description in test_scenarios:
            print(f"\n  Quantity {quantity} ({description}):")
            
            # Rule-based test
            rule_data = {
                "service_id": "printing",
                "file_id": f"quick-rule-{file_type}-{quantity}",
                "length": 100.0, "width": 50.0, "thickness": 10.0,
                "quantity": quantity, "material_id": "PA11", "material_form": "powder",
                "n_dimensions": 5, "k_type": 1.0, "k_process": 1.0,
                "cover_id": ["1"], "k_otk": 1.0, "k_cert": ["a", "f"], "location": "location_1"
            }
            
            try:
                response = requests.post(API_ENDPOINT, json=rule_data, timeout=10)
                if response.status_code == 200:
                    data = response.json()['data']
                    print(f"    🔧 Rule-based: ${data['detail_price']:,.2f} (k_quantity: {data['k_quantity']:.3f})")
                    results.append({
                        'file_type': file_type, 'method': 'rule_based', 'quantity': quantity,
                        'detail_price': data['detail_price'], 'k_quantity': data['k_quantity']
                    })
                else:
                    print(f"    ❌ Rule-based failed: {response.status_code}")
            except Exception as e:
                print(f"    ❌ Rule-based error: {e}")
            
            # ML-based test
            ml_data = {
                "service_id": "printing",
                "file_id": f"quick-ml-{file_type}-{quantity}",
                "file_data": file_data[file_type],
                "file_name": f"test.{file_type}",
                "file_type": file_type,
                "quantity": quantity, "material_id": "PA11", "material_form": "powder",
                "n_dimensions": 5, "k_type": 1.0, "k_process": 1.0,
                "cover_id": ["1"], "k_otk": 1.0, "k_cert": ["a", "f"], "location": "location_1"
            }
            
            try:
                response = requests.post(API_ENDPOINT, json=ml_data, timeout=10)
                if response.status_code == 200:
                    data = response.json()['data']
                    print(f"    🤖 ML-based: ${data['detail_price']:,.2f} (k_quantity: {data['k_quantity']:.3f})")
                    results.append({
                        'file_type': file_type, 'method': 'ml_based', 'quantity': quantity,
                        'detail_price': data['detail_price'], 'k_quantity': data['k_quantity']
                    })
                else:
                    print(f"    ❌ ML-based failed: {response.status_code}")
            except Exception as e:
                print(f"    ❌ ML-based error: {e}")
    
    # Summary
    print(f"\n✅ Quick test completed! {len(results)} successful tests.")
    
    # Check k_quantity accuracy
    correct_discounts = 0
    for result in results:
        expected = 1.0 if result['quantity'] < 21 else 0.95 if result['quantity'] < 101 else 0.85 if result['quantity'] < 501 else 0.8
        if abs(result['k_quantity'] - expected) < 0.001:
            correct_discounts += 1
    
    print(f"📈 Discount accuracy: {correct_discounts}/{len(results)} ({correct_discounts/len(results)*100:.1f}%)")
    
    return results

if __name__ == "__main__":
    quick_test()
