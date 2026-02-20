
"""Centralized UI constants (colors, fonts, sizes) for Windows."""
from __future__ import annotations
from dataclasses import dataclass, field

DEFAULT_COL_WIDTHS = {
    "CfgKey": 180,
    "Type": 110,
    "Key": 340,
    "Old": 320,
    "New": 320,
}

@dataclass(frozen=True)
class UIConfig:
    font_default: tuple[str, int] = ("Segoe UI", 10)
    font_mono: tuple[str, int] = ("Courier New", 9)

    bg_main: str = "#f5f6f7"
    bg_table: str = "#ffffff"
    bg_changed: str = "#fff4cc"
    bg_added: str = "#d9fdd3"
    bg_removed: str = "#ffd6d6"
    fg_watch: str = "#0b63d9"

    json_hit_bg: str = "#ffe24a"
    json_hit_fg: str = "#000000"

    min_width: int = 1200
    min_height: int = 750

    col_widths: dict[str, int] = field(default_factory=lambda: DEFAULT_COL_WIDTHS.copy())

CONFIG = UIConfig()
