from __future__ import annotations

class UIConfig:
    WINDOW_W = 1450
    WINDOW_H = 900
    MIN_W = 1100
    MIN_H = 720

    TREE_COLUMNS = ('CfgKey', 'Type', 'Key', 'Old', 'New')
    TREE_WIDTHS = {
        'CfgKey': 220,
        'Type': 90,
        'Key': 420,
        'Old': 330,
        'New': 330
    }

    INLINE_ROWS = 8

    COLOR_CHANGED = '#FFF5CC'  # amber
    COLOR_ADDED   = '#E6FFED'  # light green
    COLOR_REMOVED = '#FFECEC'  # light red

    COLOR_LINE_HIT_BG = '#ffeb3b'  # bright yellow
    COLOR_LINE_HIT_FG = 'black'

    DEFAULT_WATCHLIST = 'numericCurrencyCode, schemeConfigs, processingAgreements'
    DIFF_DISPLAY_LIMIT = 5000