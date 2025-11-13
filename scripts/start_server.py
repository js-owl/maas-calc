#!/usr/bin/env python3
"""
Script to start the FastAPI server
"""

import subprocess
import sys
from pathlib import Path

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting FastAPI server...")
    print("Server will be available at: http://localhost:7000")
    print("API documentation at: http://localhost:7000/docs")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Change to the project directory
        project_dir = Path(__file__).parent.parent
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "7000"
        ], cwd=project_dir)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(start_server())
