#!/usr/bin/env python3
"""
Launcher: Execute the Payload Diff Viewer using module mode to fix relative imports.
Run this from the parent directory (updated_app_and_file_loader/).
"""

import sys
from pathlib import Path
import os

def launch_app():
    """Launch the Payload Diff Viewer using proper module execution."""
    # Get the parent directory (should contain payload_viewer/)
    launcher_dir = Path(__file__).parent
    package_dir = launcher_dir / "payload_viewer"
    
    if not package_dir.exists():
        raise FileNotFoundError(f"payload_viewer/ directory not found at {package_dir}")
    
    # Verify run_app.py exists inside package
    run_app_path = package_dir / "run_app.py"
    if not run_app_path.exists():
        raise FileNotFoundError(f"run_app.py not found at {run_app_path}")
    
    # Add package directory to path
    sys.path.insert(0, str(package_dir))
    
    # Run as module to enable relative imports
    try:
        # Use subprocess to run as module (avoids relative import issues)
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "payload_viewer.run_app"
        ], cwd=str(launcher_dir), check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Failed to run application: {e}")
        raise
    except ImportError as e:
        print(f"Import error: {e}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Python path: {sys.path[:2]}")
        print(f"Package directory exists: {package_dir.exists()}")
        raise

if __name__ == "__main__":
    sys.exit(launch_app())
