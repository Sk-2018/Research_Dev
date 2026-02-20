from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

class SettingsManager:
    """JSON-backed settings stored at %USERPROFILE%\\.payloaddiff_settings.json"""

    def __init__(self, filename: Optional[str] = None) -> None:
        if filename:
            self.path = filename
        else:
            home = os.path.expanduser("~")
            self.path = os.path.join(home, ".payloaddiff_settings.json")
        self.data: Dict[str, Any] = {}
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def load(self) -> None:
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            else:
                self.data = {}
        except Exception:
            self.data = {}

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass
