"""
Entry point: Run the PayloadViewerApp with absolute imports for direct execution.
This version works when run directly with 'python run_app.py' from inside payload_viewer/.
"""

import os
import sys
from pathlib import Path

# Add current directory (payload_viewer/) to Python path for absolute imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Absolute imports (no dots)
import app
from file_loader import FileLoader
from parse_logger import ParseLogger
from settings import SettingsManager

def main() -> None:
    """Main entry point - creates dependencies and runs the app."""
    if os.name != "nt":
        print("Warning: Optimized for Windows; may need tweaks on other OS.")
    
    # Create dependencies
    logger = ParseLogger()
    settings = SettingsManager()
    loader = FileLoader(logger)
    
    # Create and run the application
    app_instance = app.PayloadViewerApp(logger, settings, loader)
    app_instance.mainloop()

if __name__ == "__main__":
    main()
