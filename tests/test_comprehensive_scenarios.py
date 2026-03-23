#!/usr/bin/env python3
"""
Comprehensive test for all scenarios: ML models, rule-based, with/without files
"""

import requests
import base64
from pathlib import Path
import time
import json

def encode_file(file_path):
    """Encode file to base64 for upload"""
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def run_scenario_test(scenario_name, payload, expected_engine=None):
    """Test a specific scenario"""
    print(f"\n{'='*80}")
    print(f"TESTING: {scenario_name}")
    print(f"Expected Engine: {expected_engine or 'Any'}")
    print(f"{'='*80}")
    
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:7000/calculate-price",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response_time = time.time() - start_time
        
        print(f"Status: {response.status_code} | Time: {response_time:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            calc_data = data.get("data", {})
            
            print(f"File: {calc_data.get('filename', 'N/A')}")
            print(f"Engine: {calc_data.get('calculation_engine', 'unknown').upper()}")
            print(f"Method: {calc_data.get('calculation_method', 'unknown')}")
            print(f"Service: {calc_data.get('service_id', 'unknown')}")
            print(f"Total Price: ${calc_data.get('total_price', 0):,.2f}")
            print(f"Total Time: {calc_data.get('total_time', 0):.3f} hours")
            print(f"Cycle: {calc_data.get('manufacturing_cycle', 'N/A')} days")
            
            # Check if engine matches expectation
            actual_engine = calc_data.get('calculation_engine', 'unknown')
            engine_match = expected_engine is None or actual_engine == expected_engine
            
            if actual_engine == 'ml_model':
                print(f"\n🤖 ML MODEL RESULTS:")
                print(f"   ML Prediction: {calc_data.get('ml_prediction_hours', 0):.3f} hours")
                
                features = calc_data.get('features_extracted', {})
                if features:
                    print(f"   Volume: {features.get('volume', 0):,.1f} cm³")
                    print(f"   Surface Area: {features.get('surface_area', 0):,.1f} cm²")
                    obb_x = features.get('obb_x', 0)
                    obb_y = features.get('obb_y', 0)
                    obb_z = features.get('obb_z', 0)
                    print(f"   OBB: {obb_x:.1f} × {obb_y:.1f} × {obb_z:.1f} cm")
                    print(f"   Faces: {features.get('face_count', 0)}")
                    print(f"   Vertices: {features.get('vertex_count', 0)}")
                    print(f"   Lathe Suitable: {'Yes' if features.get('check_sizes_for_lathe', 0) else 'No'}")
            else:
                print(f"\n📐 RULE-BASED CALCULATION")
                print(f"   (No ML features or models unavailable)")
            
            return {
                'success': True,
                'engine': actual_engine,
                'engine_match': engine_match,
                'response_time': response_time,
                'total_price': calc_data.get('total_price', 0),
                'total_time': calc_data.get('total_time', 0),
                'service_id': calc_data.get('service_id', 'unknown'),
                'method': calc_data.get('calculation_method', 'unknown')
            }
            
        else:
            print(f"❌ ERROR: {response.text}")
            return {
                'success': False,
                'error': response.text,
                'status_code': response.status_code
            }
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def test_stl_ml_scenarios():
    """Test STL file with ML models for all processes"""
    print("\n" + "="*80)
    print("🧪 TESTING STL FILE WITH ML MODELS")
    print("="*80)
    
    stl_file_data = encode_file('test_files/02.stl')
    stl_tests = [
        # ("STL + Printing (ML)", {
        #     "service_id": "printing",
        #     "file_id": "test-stl-printing",
        #     "file_data": stl_file_data,
        #     "file_name": "02.stl",
        #     "file_type": "stl",
        #     "quantity": 1,
        #     "material_id": "PA11",
        #     "material_form": "powder",
        #     "cover_id": ["1"],
        #     "n_dimensions": 3,
        #     "k_type": 1.0,
        #     "k_process": 1.0
        # }, "ml_model"),
        
        # ("STL + CNC Milling (ML)", {
        #     "service_id": "cnc-milling",
        #     "file_id": "test-stl-milling",
        #     "file_data": stl_file_data,
        #     "file_name": "02.stl",
        #     "file_type": "stl",
        #     "quantity": 1,
        #     "material_id": "alum_D16",
        #     "material_form": "sheet",
        #     "cover_id": ["1"],
        #     "tolerance_id": "1",
        #     "finish_id": "1"
        # }, "rule_based"),
        
        # ("STL + CNC Lathe (ML)", {
        #     "service_id": "cnc-lathe",
        #     "file_id": "test-stl-lathe",
        #     "file_data": stl_file_data,
        #     "file_name": "02.stl",
        #     "file_type": "stl",
        #     "quantity": 1,
        #     "material_id": "alum_D16",
        #     "material_form": "rod",
        #     "cover_id": ["1"],
        #     "tolerance_id": "1",
        #     "finish_id": "1"
        # }, "rule_based"),
        
        # ("STL + Painting (ML)", {
        #     "service_id": "painting",
        #     "file_id": "test-stl-painting",
        #     "file_data": stl_file_data,
        #     "file_name": "02.stl",
        #     "file_type": "stl",
        #     "quantity": 1,
        #     "material_id": "PA11",
        #     "material_form": "powder",
        #     "cover_id": ["1"],
        #     "tolerance_id": "1",
        #     "finish_id": "1",
        #     "paint_type": "a",
        #     "paint_prepare": "b",
        #     "paint_primer": "b",
        #     "paint_lakery": "a",
        #     "control_type": "1"
        # }, "ml_model")
    ]
    
    results = []
    for test_name, payload, expected_engine in stl_tests:
        result = run_scenario_test(test_name, payload, expected_engine)
        result['test_name'] = test_name
        results.append(result)
    
    # Assert all tests passed
    for result in results:
        assert result['success'], f"Test {result['test_name']} failed: {result.get('error', 'Unknown error')}"
        if expected_engine:
            assert result['engine'] == expected_engine, f"Expected {expected_engine}, got {result['engine']}"
    
    return results

def test_stp_ml_scenarios():
    """Test STP file with ML models for all processes"""
    print("\n" + "="*80)
    print("🧪 TESTING STP FILE WITH ML MODELS")
    print("="*80)
    
    stp_file_data = encode_file('test_files/S8000_125_63_293_001_D000_02.stp')
    stp_tests = [
        # ("STP + Printing (ML)", {
        #     "service_id": "printing",
        #     "file_id": "test-stp-printing",
        #     "file_data": stp_file_data,
        #     "file_name": "S8000_125_63_293_001_D000_02.stp",
        #     "file_type": "stp",
        #     "quantity": 1,
        #     "material_id": "PA11",
        #     "material_form": "powder",
        #     "cover_id": ["1"],
        #     "n_dimensions": 3,
        #     "k_type": 1.0,
        #     "k_process": 1.0
        # }, "ml_model"),
        
        ("STP + CNC Milling (ML)", {
            "service_id": "cnc-milling",
            "file_id": "test-stp-milling",
            "file_data": stp_file_data,
            "file_name": "S8000_125_63_293_001_D000_02.stp",
            "file_type": "stp",
            "quantity": 1,
            "material_id": "alum_D16",
            "material_form": "sheet",
            "cover_id": ["1"],
            "tolerance_id": "1",
            "finish_id": "1"
        }, "ml_model"),
        
        ("STP + CNC Lathe (ML)", {
            "service_id": "cnc-lathe",
            "file_id": "test-stp-lathe",
            "file_data": stp_file_data,
            "file_name": "S8000_125_63_293_001_D000_02.stp",
            "file_type": "stp",
            "quantity": 1,
            "material_id": "alum_D16",
            "material_form": "rod",
            "cover_id": ["1"],
            "tolerance_id": "1",
            "finish_id": "1"
        }, "ml_model"),
        
        # ("STP + Painting (ML)", {
        #     "service_id": "painting",
        #     "file_id": "test-stp-painting",
        #     "file_data": stp_file_data,
        #     "file_name": "S8000_125_63_293_001_D000_02.stp",
        #     "file_type": "stp",
        #     "quantity": 1,
        #     "material_id": "PA11",
        #     "material_form": "powder",
        #     "cover_id": ["1"],
        #     "tolerance_id": "1",
        #     "finish_id": "1",
        #     "paint_type": "a",
        #     "paint_prepare": "b",
        #     "paint_primer": "b",
        #     "paint_lakery": "a",
        #     "control_type": "1"
        # }, "ml_model")
    ]
    
    results = []
    for test_name, payload, expected_engine in stp_tests:
        result = run_scenario_test(test_name, payload, expected_engine)
        result['test_name'] = test_name
        results.append(result)
    
    # Assert all tests passed
    for result in results:
        assert result['success'], f"Test {result['test_name']} failed: {result.get('error', 'Unknown error')}"
        if expected_engine:
            assert result['engine'] == expected_engine, f"Expected {expected_engine}, got {result['engine']}"
    
    return results

def test_rule_based_scenarios():
    """Test rule-based calculations (no file, dimensions only)"""
    print("\n" + "="*80)
    print("🧪 TESTING RULE-BASED CALCULATIONS (NO FILE)")
    print("="*80)
    
    rule_based_tests = [
        ("Rule-Based Printing", {
            "service_id": "printing",
            "file_id": "test-rule-printing",
            "dimensions": {
                "length": 100.0,
                "width": 50.0,
                "height": 10.0
            },
            "quantity": 1,
            "material_id": "PA11",
            "material_form": "powder",
            "cover_id": ["1"],
            "k_type": 1.0,
            "k_process": 1.0
        }, "rule_based"),
        
        ("Rule-Based CNC Milling", {
            "service_id": "cnc-milling",
            "file_id": "test-rule-milling",
            "dimensions": {
                "length": 80.0,
                "width": 60.0,
                "height": 15.0
            },
            "quantity": 1,
            "material_id": "alum_D16",
            "material_form": "sheet",
            "cover_id": ["1"],
            "tolerance_id": "1",
            "finish_id": "1"
        }, "rule_based"),
        
        ("Rule-Based CNC Lathe", {
            "service_id": "cnc-lathe",
            "file_id": "test-rule-lathe",
            "dimensions": {
                "length": 50.0,
                "width": 50.0,
                "height": 100.0
            },
            "quantity": 1,
            "material_id": "alum_D16",
            "material_form": "rod",
            "cover_id": ["1"],
            "tolerance_id": "1",
            "finish_id": "1"
        }, "rule_based"),
        
        ("Rule-Based Painting", {
            "service_id": "painting",
            "file_id": "test-rule-painting",
            "dimensions": {
                "length": 120.0,
                "width": 80.0,
                "height": 5.0
            },
            "quantity": 1,
            "material_id": "PA11",
            "material_form": "powder",
            "cover_id": ["1"],
            "tolerance_id": "1",
            "finish_id": "1",
            "paint_type": "a",
            "paint_prepare": "b",
            "paint_primer": "b",
            "paint_lakery": "a",
            "control_type": "1"
        }, "rule_based")
    ]
    
    results = []
    for test_name, payload, expected_engine in rule_based_tests:
        result = run_scenario_test(test_name, payload, expected_engine)
        result['test_name'] = test_name
        results.append(result)
    
    # Assert all tests passed
    for result in results:
        assert result['success'], f"Test {result['test_name']} failed: {result.get('error', 'Unknown error')}"
        if expected_engine:
            assert result['engine'] == expected_engine, f"Expected {expected_engine}, got {result['engine']}"
    
    return results

def main():
    """Run comprehensive test scenarios"""
    print("🧪 COMPREHENSIVE API TESTING")
    print("="*80)
    print("Testing all scenarios: ML models, rule-based, with/without files")
    print("="*80)
    
    # Check server
    try:
        health_response = requests.get("http://localhost:7000/health", timeout=5)
        print(f"Server Status: {health_response.status_code} ✅")
    except Exception as e:
        print(f"Server Error: {e} ❌")
        return
    
    all_results = []
    
    # Test 1: STL file with ML models
    stl_results = test_stl_ml_scenarios()
    all_results.extend(stl_results)
    
    # Test 2: STP file with ML models
    stp_results = test_stp_ml_scenarios()
    all_results.extend(stp_results)
    
    # Test 3: Rule-based calculations (no file)
    rule_results = test_rule_based_scenarios()
    all_results.extend(rule_results)
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    successful_tests = [r for r in all_results if r.get('success', False)]
    failed_tests = [r for r in all_results if not r.get('success', False)]
    ml_tests = [r for r in successful_tests if r.get('engine') == 'ml_model']
    rule_tests = [r for r in successful_tests if r.get('engine') == 'rule_based']
    engine_matches = [r for r in successful_tests if r.get('engine_match', False)]
    
    print(f"Total Tests: {len(all_results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"ML Model: {len(ml_tests)}")
    print(f"Rule-Based: {len(rule_tests)}")
    print(f"Engine Matches: {len(engine_matches)}")
    
    if successful_tests:
        avg_response_time = sum(r.get('response_time', 0) for r in successful_tests) / len(successful_tests)
        print(f"Average Response Time: {avg_response_time:.2f}s")
        
        print(f"\n✅ SUCCESSFUL TESTS:")
        for result in successful_tests:
            engine_status = "🤖 ML" if result.get('engine') == 'ml_model' else "📐 RULE"
            match_status = "✅" if result.get('engine_match', False) else "❌"
            print(f"   {result['test_name']}: {engine_status} {match_status} - ${result.get('total_price', 0):,.2f}")
    
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for result in failed_tests:
            print(f"   {result['test_name']}: {result.get('error', 'Unknown error')}")
    
    print(f"\n{'='*80}")
    print("🎯 COMPREHENSIVE TEST COMPLETE")
    print(f"{'='*80}")
    
    return all_results

if __name__ == "__main__":
    results = main()
