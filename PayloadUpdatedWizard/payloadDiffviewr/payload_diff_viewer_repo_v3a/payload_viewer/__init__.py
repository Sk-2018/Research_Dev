
"""Payload Diff Viewer package (Windows-first Tkinter app)."""
from __future__ import annotations
__all__ = ["__version__", "launch"]
__version__ = "1.0.2"
def launch() -> None:
    from .app import main
    main()
