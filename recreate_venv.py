#!/usr/bin/env python3
"""
Script to recreate virtual environment and install dependencies
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Success: {description}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {description}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main function to recreate virtual environment"""
    print("🚀 Recreating Virtual Environment and Installing Dependencies")
    print("="*70)
    
    # Get current directory
    project_dir = Path.cwd()
    venv_dir = project_dir / "venv"
    requirements_file = project_dir / "requirements2.txt"
    
    print(f"Project directory: {project_dir}")
    print(f"Virtual environment: {venv_dir}")
    print(f"Requirements file: {requirements_file}")
    
    # Check if requirements2.txt exists
    if not requirements_file.exists():
        print(f"❌ Requirements file not found: {requirements_file}")
        return False
    
    # Step 1: Remove existing virtual environment
    if venv_dir.exists():
        print(f"\n🗑️ Removing existing virtual environment...")
        try:
            shutil.rmtree(venv_dir)
            print("✅ Virtual environment removed")
        except Exception as e:
            print(f"❌ Error removing virtual environment: {e}")
            return False
    else:
        print("ℹ️ No existing virtual environment found")
    
    # Step 2: Create new virtual environment with Python 3.11
    python311_path = r"C:\Users\vitalyd\AppData\Local\Programs\Python\Python311\python.exe"
    if not run_command(f'"{python311_path}" -m venv venv', "Creating new virtual environment with Python 3.11"):
        return False
    
    # Step 3: Determine activation script path
    if os.name == 'nt':  # Windows
        activate_script = venv_dir / "Scripts" / "activate.bat"
        pip_path = venv_dir / "Scripts" / "pip.exe"
        python_path = venv_dir / "Scripts" / "python.exe"
    else:  # Unix/Linux/macOS
        activate_script = venv_dir / "bin" / "activate"
        pip_path = venv_dir / "bin" / "pip"
        python_path = venv_dir / "bin" / "python"
    
    # Step 4: Upgrade pip first
    if not run_command(f'"{python_path}" -m pip install --upgrade pip', "Upgrading pip"):
        return False
    
    # Step 5: Install wheel and setuptools
    if not run_command(f'"{python_path}" -m pip install wheel setuptools', "Installing wheel and setuptools"):
        return False
    
    # Step 6: Install dependencies from requirements2.txt
    if not run_command(f'"{python_path}" -m pip install -r requirements2.txt', "Installing dependencies from requirements2.txt"):
        return False
    
    # Step 7: Verify installation
    print(f"\n🔍 Verifying installation...")
    if not run_command(f'"{python_path}" -c "import fastapi, uvicorn, trimesh, cadquery, xgboost, pandas, numpy; print(\'All key packages imported successfully\')"', "Verifying key packages"):
        return False
    
    print(f"\n🎉 Virtual environment recreation completed successfully!")
    print(f"\nTo activate the virtual environment:")
    if os.name == 'nt':  # Windows
        print(f"  venv\\Scripts\\activate")
    else:  # Unix/Linux/macOS
        print(f"  source venv/bin/activate")
    
    print(f"\nTo start the server:")
    print(f"  uvicorn main:app --reload --host 0.0.0.0 --port 7000")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
