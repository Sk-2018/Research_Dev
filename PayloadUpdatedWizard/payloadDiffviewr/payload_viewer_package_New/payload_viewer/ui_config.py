from __future__ import annotations

class UIConfig:
    """Central UI constants used across the app."""

    # Window
    WINDOW_W = 1450
    WINDOW_H = 900
    MIN_W = 1100
    MIN_H = 720

    # Diff table
    TREE_COLUMNS = ("CfgKey", "Type", "Key", "Old", "New")
    TREE_WIDTHS = {
        "CfgKey": 220,
        "Type": 90,
        "Key": 420,
        "Old": 330,
        "New": 330,
    }

    # Inline diff pane default height (rows)
    INLINE_ROWS = 8

    # Highlight colors
    COLOR_CHANGED = "#FFF5CC"  # amber (row background)
    COLOR_ADDED = "#E6FFED"    # light green
    COLOR_REMOVED = "#FFECEC"  # light red

    # Strong line highlight (works on Windows light/dark)
    COLOR_LINE_HIT_BG = "#ffeb3b"
    COLOR_LINE_HIT_FG = "black"

    # Defaults
    DEFAULT_WATCHLIST = "numericCurrencyCode, schemeConfigs, processingAgreements"
    DIFF_DISPLAY_LIMIT = 5000

    # Summary dashboard defaults (kept for future use)
    SUMMARY_TOPN_DEFAULT = 25
    SUMMARY_MAXLBL_DEFAULT = 80
    SUMMARY_FIG_DPI = 100
    SUMMARY_FIG_W = 8.0
    SUMMARY_FIG_H = 5.0
