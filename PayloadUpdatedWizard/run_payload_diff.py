"""
Launcher for PayloadDiff viewer.
Tries to run the PyQt frontend if PyQt6/PyQt5 is available; otherwise falls back
to the original Tkinter-based script.

Usage:
    python run_payload_diff.py        # prefer PyQt if installed
    python run_payload_diff.py --tk  # force Tkinter launcher
"""
import sys
import subprocess
import shutil
import os

HERE = os.path.dirname(__file__)
PYQT_MODULES = ('PyQt6', 'PyQt5')
PYQT_SCRIPT = 'GeminiPayloadDiff_GeminiUltra_FIXED_optimized_FULL_PyQt.py'
TK_SCRIPT = 'GeminiPayloadDiff_GeminiUltra_FIXED_optimized_FIXED.py'

def has_pyqt():
    for m in PYQT_MODULES:
        try:
            __import__(m)
            return True
        except Exception:
            continue
    return False

if __name__ == '__main__':
    force_tk = '--tk' in sys.argv or '-t' in sys.argv
    if not force_tk and has_pyqt():
        script = os.path.join(HERE, PYQT_SCRIPT)
        if os.path.exists(script):
            print('Launching PyQt frontend...')
            subprocess.run([sys.executable, script])
            sys.exit(0)
        else:
            print('PyQt frontend not found, falling back to Tkinter.')
    # fallback to tkinter
    script = os.path.join(HERE, TK_SCRIPT)
    if os.path.exists(script):
        print('Launching Tkinter frontend...')
        subprocess.run([sys.executable, script])
    else:
        print('No frontend found. Expected files:')
        print('  ', PYQT_SCRIPT)
        print('  ', TK_SCRIPT)
        sys.exit(2)
