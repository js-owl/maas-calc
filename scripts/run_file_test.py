#!/usr/bin/env python3
"""
Quick launcher for the Interactive File Upload Test Script

This script provides a simple way to run the interactive file test
with proper error handling and environment setup.
"""

import sys
import os
from pathlib import Path

def check_requirements():
    """Check if required packages are available"""
    try:
        import requests
        return True
    except ImportError:
        print("❌ Error: 'requests' package not found")
        print("Please install it with: pip install requests")
        return False

def check_api_connection():
    """Check if API is running"""
    try:
        import requests
        response = requests.get("http://localhost:7000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Main launcher function"""
    print("🚀 Manufacturing Calculation File Upload Test Launcher")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check API connection
    print("🔍 Checking API connection...")
    if not check_api_connection():
        print("❌ API not running or not accessible at http://localhost:7000")
        print("Please start the API server first:")
        print("  python main.py")
        print("  or")
        print("  uvicorn main:app --reload --host 0.0.0.0 --port 7000")
        sys.exit(1)
    
    print("✅ API connection successful")
    
    # Check test files directory
    test_files_dir = Path("test_files")
    if not test_files_dir.exists():
        print(f"❌ Test files directory not found: {test_files_dir}")
        print("Please create the directory and add some STL/STP files for testing")
        sys.exit(1)
    
    # Count test files
    test_files = list(test_files_dir.glob("*.stl")) + list(test_files_dir.glob("*.stp")) + list(test_files_dir.glob("*.step"))
    if not test_files:
        print(f"❌ No STL/STP files found in {test_files_dir}")
        print("Please add some test files to the test_files directory")
        sys.exit(1)
    
    print(f"✅ Found {len(test_files)} test files")
    
    # Launch interactive test
    print("\n🎯 Launching Interactive File Upload Test...")
    print("=" * 60)
    
    try:
        from interactive_file_test import main as run_interactive_test
        run_interactive_test()
    except ImportError as e:
        print(f"❌ Error importing interactive test: {e}")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

