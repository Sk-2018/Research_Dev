import sys

# --- Fonts ---
# Use Segoe UI on Windows, default sans-serif elsewhere
DEFAULT_FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"
FONT_NORMAL = (DEFAULT_FONT_FAMILY, 9)
FONT_BOLD = (DEFAULT_FONT_FAMILY, 9, "bold")
FONT_CODE = ("Courier New", 9)

# --- Colors ---
COLOR_BG_DEFAULT = "#f0f0f0"
COLOR_BG_WIDGET = "#ffffff"
COLOR_BG_TEXT = "#fdfdfd"
COLOR_BG_TEXT_READONLY = "#f5f5f5"
COLOR_FG_TEXT = "#000000"

# Diff Table Colors
COLOR_TAG_CHANGED = ("#fff5e6", "#000000")  # light orange bg, black text
COLOR_TAG_ADDED = ("#e6ffec", "#000000")    # light green bg, black text
COLOR_TAG_REMOVED = ("#ffe6e6", "#000000")  # light red bg, black text
COLOR_TAG_WATCH = ("#e6f2ff", "#0000ff")    # light blue bg, blue text (bolded in app)

# Full JSON Pane Highlight
COLOR_HIGHLIGHT_BG = "#ffe24a"  # bright yellow
COLOR_HIGHLIGHT_FG = "#000000"  # black

# Summary Dashboard
COLOR_SUMMARY_TOTAL_BG = "#e0e0e0"
COLOR_SUMMARY_TOTAL_FG = "#000000"

# --- Column Widths (example values) ---
DIFF_TABLE_COLUMNS = {
    "CfgKey": 200,
    "Type": 100,
    "Key": 350,
    "Old": 300,
    "New": 300
}

# --- Default Sizes ---
DEFAULT_APP_GEOMETRY = "1200x800"
DEFAULT_SUMMARY_GEOMETRY = "700x500"