
"""
Payload Diff Viewer package (Windows-first Tkinter app).

Exposes the package version and a `launch()` helper to start the app.
"""
from __future__ import annotations

__all__ = ["__version__", "launch"]
__version__: str = "1.0.0"


def launch() -> None:
    """Start the Tkinter application."""
    # Lazy import to avoid importing Tk at module import time.
    from .app import main
    main()
