#!/usr/bin/env python3
"""Run the S3 Vector Dashboard."""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the Streamlit dashboard."""
    # Set environment variables if not already set
    if not os.getenv('VECTOR_BUCKET'):
        print("Warning: VECTOR_BUCKET not set")
    
    if not os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = 'us-east-1'
    
    # Get dashboard path
    dashboard_path = Path(__file__).parent / "src" / "dashboard" / "app.py"
    
    # Run streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        str(dashboard_path),
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ]
    
    print(f"Starting dashboard at http://localhost:8501")
    print(f"Command: {' '.join(cmd)}")
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()