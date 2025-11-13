#!/usr/bin/env python3
"""
Master test script that runs all tests
"""

import subprocess
import sys
from pathlib import Path

def run_test_script(script_name):
    """Run a test script and return success status"""
    print(f"\nRunning {script_name}...")
    print("-" * 30)
    
    try:
        result = subprocess.run([
            sys.executable, script_name
        ], cwd=Path(__file__).parent, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False

def main():
    """Run all test scripts"""
    print("Running All Tests for Unified Endpoint")
    print("=" * 50)
    
    test_scripts = [
        "test_unified_endpoint.py",
        "test_file_upload.py"
    ]
    
    passed = 0
    total = len(test_scripts)
    
    for script in test_scripts:
        if run_test_script(script):
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test suites passed: {passed}/{total}")
    
    if passed == total:
        print("All test suites passed!")
        return 0
    else:
        print("Some test suites failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
