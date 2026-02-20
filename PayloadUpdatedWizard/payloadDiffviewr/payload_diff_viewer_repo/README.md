
# Payload Diff Viewer (Windows, Tkinter)

A Windows-first Tkinter app to compare **CURRENT vs OLD** JSON payloads from CSV/TSV/TXT/Excel files using DeepDiff.
Includes a Summary Dashboard with an optional matplotlib chart.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install "deepdiff>=6.7.1" "pandas>=2.0.0" "openpyxl>=3.1.2" "matplotlib>=3.8.0" "orjson>=3.9.15"
```

## Run

```bash
python run_app.py
```

## Notes
- **Excel support**: `.xlsx` via openpyxl. `.xls` is not supported; re-save as `.xlsx`.
- **Default folder**: File → Set Default Folder… or from SharePoint URL (mapped to UNC if accessible).
- **Keyboard**: Ctrl+O (Open), F5 (Compare), Ctrl+M (Summary).
- No custom icons on matplotlib figures to avoid Tk iconphoto issues.
