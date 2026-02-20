
from __future__ import annotations
__all__ = ["__version__", "launch"]
__version__ = "1.0.3"
def launch() -> None:
    from .app import main
    main()
