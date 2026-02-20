
"""Payload Diff Viewer package (Windows-first Tkinter app)."""
from __future__ import annotations

__all__ = ["__version__", "launch"]
__version__: str = "1.0.1"

def launch() -> None:
    """Start the Tkinter application."""
    from .app import main  # lazy import
    main()
