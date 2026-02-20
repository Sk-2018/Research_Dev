# PayloadDiffViewer Tool – Mentor Walkthrough

Generated: 2025-12-16 06:01:48

This guide explains the **intent** behind the code and how the pieces fit together. I reference **line numbers** from `PayloadDiffViewer_Tool_FIXED_v2.py`.

## Big idea (what this script is doing)

- This is a **Tkinter desktop app** that loads a CSV/XLSX export of configuration payloads.
- It **auto-detects columns** like `Config Name`, `Config Key`, `CURRENT PAYLOAD`, `OLD PAYLOAD`.
- For a selected config and keys, it parses the payload strings into JSON-like objects and runs **DeepDiff**.
- Then it renders differences in a table, shows payload panes, supports watch-list filtering, and exports.

## Why the 'No Rows' bug happened (and what we fixed)

- Excel sometimes stores big IDs as **scientific notation** (e.g., `5.318722E+18`).
- The UI Listbox showed **formatted** keys, but matching used the **raw** key strings.
- Result: selected keys never equaled raw keys → 0 matches → “No Rows”.
- Fix: build a `display_to_raw` mapping during list population, then resolve selected display keys back to raw.
- Also: `_format_key` must be a method of the correct class (otherwise Tkinter fallback causes AttributeError).

## File map (how to read it)

### 1) Module header + imports
- Lines 1–120-ish: docstring and imports.
- Goal: bring in tkinter, pandas, openpyxl, DeepDiff, and helpers.

### 2) Major components / anchors
- **Config class** starts at line **122**
- **ParseLogger class** starts at line **213**
- **RowMeta class** starts at line **683**
- **App class** starts at line **699**
- **on_name_selected** starts at line **1243**
- **_format_key** starts at line **1920**
- **_get_rows_for_keys_map** starts at line **1283**

## Component explanations

### Config (settings + validation)

- Starts around line **122**.
- Holds constants and knobs: regex for config name, column aliases, defaults.
- `validate_config_name()` enforces a clean name so bad rows don’t pollute the UI.

### ParseLogger (collecting non-fatal parse warnings)
- Starts around line **213**.
- When parsing JSON-ish strings fails, we don’t want to crash.
- This object collects warnings and can show a summary dialog.

### Helper functions (JSON parsing + DeepDiff path helpers)
- There are several module-level helpers like `parse_jsonish_verbose`, `pretty_json`, and path utilities.
- Purpose: normalize messy JSON payload strings and convert DeepDiff paths to readable keys.

### PayloadDiffViewerApp (the main Tkinter window)
- Starts around line **699**.
- This is the top-level `tk.Tk` subclass.
- Responsibilities:
  - Build UI controls (combobox, listbox, tree, text panes)
  - Load files (CSV/XLSX)
  - Build indexes: `by_name` mapping config name → row indices
  - Handle selection events and run comparisons
  - Export results

### `on_name_selected` (populate the Config Keys list)
- Around line **1243**.
- When user picks a Config Name:
  - Look up all row indices for that name (`by_name[name]`).
  - Extract raw `Config Key` values.
  - Format for display (optional) **and** build `display_to_raw` mapping.
  - Insert display keys into the listbox.

### `_format_key` (make Config Key display stable)
- Around line **1920**.
- Uses `Decimal` instead of `float` to avoid rounding/precision loss for 18+ digit IDs.
- Only affects display; matching uses raw keys.

### `_get_rows_for_keys_map` (row retrieval for selected keys)
- Around line **1283**.
- This is where “No Rows” used to happen.
- It now resolves selected keys to **raw** keys and matches them against each row’s raw `Config Key`.

## How the data pipeline flows end-to-end
1. **Open file** → pandas reads data.
2. **Column detection** → map user columns to internal standard names.
3. **Normalize rows** → store list of row dicts.
4. **Index** → build `by_name` dict to quickly filter by Config Name.
5. **Select Config Name** → populate key listbox (build display_to_raw).
6. **Select keys + Compare** → fetch rows, parse payload JSON, DeepDiff, populate tree.
7. **Click diff row** → show inline diff + old/new payload panes.
8. **Export** → save results.
