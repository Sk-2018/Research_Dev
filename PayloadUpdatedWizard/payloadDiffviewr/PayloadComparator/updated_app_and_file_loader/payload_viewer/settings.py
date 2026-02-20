import json
import os
from pathlib import Path
from typing import Any, Optional

DEFAULT_SETTINGS_FILE = Path.home() / ".payloaddiff_settings.json"

class SettingsManager:
    """
    Manages loading and saving user settings from a JSON file
    in the user's home directory.
    """

    def __init__(self, path: Optional[str | Path] = None) -> None:
        """
        Initializes the SettingsManager.

        Args:
            path: Optional path to the settings file. Defaults to
                  ~/.payloaddiff_settings.json
        """
        self.path = Path(path) if path else DEFAULT_SETTINGS_FILE
        self._settings: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Loads settings from the JSON file. If file not found, starts empty."""
        if not self.path.exists():
            self._settings = {}
            return
        
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                self._settings = json.load(f)
            if not isinstance(self._settings, dict):
                self._settings = {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load settings from {self.path}: {e}")
            self._settings = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Gets a value from settings.

        Args:
            key: The setting key to retrieve.
            default: The value to return if key is not found.

        Returns:
            The setting value or the default.
        """
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Sets a value in settings. Does not save automatically.

        Args:
            key: The setting key to set.
            value: The value to store.
        """
        self._settings[key] = value

    def save(self) -> None:
        """Saves the current settings to the JSON file."""
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4)
        except IOError as e:
            print(f"Error: Could not save settings to {self.path}: {e}")