
"""Simple JSON-based settings manager.

Path: ~/.payloaddiff_settings.json
Keys: default_open_dir
"""
from __future__ import annotations


import json
import os
from dataclasses import dataclass
from typing import Any

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".payloaddiff_settings.json")


@dataclass
class SettingsManager:
    path: str | None = None

    def __post_init__(self) -> None:
        if self.path is None:
            self.path = SETTINGS_FILE
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self.path or ""):
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            else:
                self._data = {}
        except Exception:
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def save(self) -> None:
        try:
            with open(self.path or SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            # Silently ignore to avoid user disruption
            pass
