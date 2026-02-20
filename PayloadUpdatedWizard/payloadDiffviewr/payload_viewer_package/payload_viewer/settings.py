from __future__ import annotations
import os, json
from typing import Any, Dict

class SettingsManager:
    """JSON-backed settings. Default file: %USERPROFILE%\\.payloaddiff_settings.json"""
    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(os.path.expanduser("~"), ".payloaddiff_settings.json")
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f) or {}
            else:
                self._data = {}
        except Exception:
            self._data = {}

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value