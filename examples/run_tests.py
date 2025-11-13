#!/usr/bin/env python3
"""
Test Runner for Manufacturing Calculations API

This script provides an easy way to run different categories of tests
for the Manufacturing Calculations API.
"""

import sys
import os
import argparse

# Add parent directory to path to import constants
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import APP_VERSION
from api_test_examples import (
    run_all_tests,
    test_health_endpoint,
    test_services_endpoint,
    test_materials_endpoint,
    test_coefficients_endpoint,
    test_comprehensive_materials,
    test_all_tolerance_finish_combinations,
    test_all_cover_types,
    test_all_paint_types,
    test_with_file_upload
)

def main():
    parser = argparse.ArgumentParser(description=f'Run API tests for Manufacturing Calculations API v{APP_VERSION}')
    parser.add_argument('--category', '-c', 
                       choices=['all', 'basic', 'materials', 'tolerance', 'cover', 'paint', 'file', 'health'],
                       default='all',
                       help='Test category to run')
    parser.add_argument('--url', '-u',
                       default='http://localhost:7000',
                       help='Base URL for the API (default: http://localhost:7000)')
    
    args = parser.parse_args()
    
    # Update the base URL if provided
    if args.url != 'http://localhost:7000':
        import api_test_examples
        api_test_examples.BASE_URL = args.url
        api_test_examples.API_ENDPOINT = f"{args.url}/calculate-price"
    
    print(f"🚀 Running Manufacturing Calculations API v{APP_VERSION} Tests")
    print(f"📡 API URL: {args.url}")
    print(f"📋 Test Category: {args.category}")
    print("="*80)
    
    try:
        if args.category == 'all':
            run_all_tests()
        elif args.category == 'basic':
            test_health_endpoint()
            test_services_endpoint()
            test_materials_endpoint()
            test_coefficients_endpoint()
        elif args.category == 'materials':
            test_comprehensive_materials()
        elif args.category == 'tolerance':
            test_all_tolerance_finish_combinations()
        elif args.category == 'cover':
            test_all_cover_types()
        elif args.category == 'paint':
            test_all_paint_types()
        elif args.category == 'file':
            test_with_file_upload()
        elif args.category == 'health':
            test_health_endpoint()
        
        print("\n✅ All tests completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
