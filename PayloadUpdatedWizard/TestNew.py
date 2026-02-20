# -*- coding: utf-8 -*-
"""
PayloadAllInOne.py

PHASE 1: Loading & Formatting module extracted and refactored from the original
PayloadDiffViewerApp codebase. This file sets up a clean, testable structure
for reading CSV/TSV/TXT and Excel (XLSX/XLS) sources with delimiter detection,
chunked loading, header scoring, and basic cleansing, ready for later phases
(DeepDiff integration, Summary Dashboard, Settings, and full Tk GUI).

Install (optional but recommended):
    pip install deepdiff pandas openpyxl matplotlib orjson
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1) App Entry / Imports Section
#    - Import order: built-in -> third-party -> internal (none yet)
# ---------------------------------------------------------------------------

# Built-in
import os
import re
import csv
import sys
import time
from json import JSONDecodeError
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# Third-party (all optional; we degrade gracefully if missing)
try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - missing dependency at runtime
    pd = None  # type: ignore

# For Excel reading via pandas. If missing, pandas will raise at runtime.
# (No direct openpyxl import required here.)

# Optional libs (future phases; kept here to centralize imports)
try:
    import matplotlib  # type: ignore
except Exception:  # pragma: no cover
    matplotlib = None  # type: ignore

try:
    import orjson  # type: ignore
except Exception:  # pragma: no cover
    orjson = None  # type: ignore

try:
    from deepdiff import DeepDiff  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover
    DeepDiff = None  # type: ignore

# Tkinter only used by ParseLogger.show(); safe to import.
import tkinter as tk  # type: ignore
from tkinter import ttk, messagebox  # type: ignore


# ---------------------------------------------------------------------------
# 2) UIConfig
# ---------------------------------------------------------------------------

class UIConfig:
    """
    Centralized UI/layout constants (used mainly by GUI; retained here so
    future phases can keep a single source of truth).
    """
    WINDOW_W: int = 1450
    WINDOW_H: int = 900
    MIN_W: int = 1100
    MIN_H: int = 720

    TREE_COLUMNS: Tuple[str, ...] = ('CfgKey', 'Type', 'Key', 'Old', 'New')
    TREE_WIDTHS: Dict[str, int] = {
        'CfgKey': 220,
        'Type': 90,
        'Key': 420,
        'Old': 330,
        'New': 330
    }

    # Colors
    COLOR_CHANGED: str = '#FFF5CC'
    COLOR_ADDED: str = '#E6FFED'
    COLOR_REMOVED: str = '#FFECEC'
    COLOR_LINE_HIT_BG: str = '#ffeb3b'
    COLOR_LINE_HIT_FG: str = 'black'

    # Defaults
    DEFAULT_WATCHLIST: str = 'numericCurrencyCode, schemeConfigs, processingAgreements'

    # Settings file location (future SettingsManager will use this)
    SETTINGS_FILE: str = os.path.expanduser('~/.payloaddiff_settings.json')


# ---------------------------------------------------------------------------
# 3) ParseLogger
# ---------------------------------------------------------------------------

class ParseLogger:
    """
    Lightweight, UI-friendly logger for parsing/IO warnings and errors.
    Use log(level='warning'|'error') to record events.

    Examples
    --------
    >>> log = ParseLogger()
    >>> log.log("Delimiter fallback to comma", level="warning", context="file.csv")
    >>> print(log.summary_text())
    """

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    def log(self, message: str, level: str = 'warning', context: str = '') -> None:
        self.entries.append({
            'timestamp': time.time(),
            'level': level,
            'message': message,
            'context': (context or '')[:200]
        })

    def summary_text(self, limit: int = 200) -> str:
        if not self.entries:
            return "No warnings or errors recorded."
        lines = ["=" * 64, f"Parse Log (last {min(limit, len(self.entries))} of {len(self.entries)})", "=" * 64, ""]
        for e in self.entries[-limit:]:
            ts = time.strftime('%H:%M:%S', time.localtime(e['timestamp']))
            lines.append(f"[{ts}] {e['level'].upper()}: {e['message']}")
            if e['context']:
                lines.append(f"  Context: {e['context']}")
        return "\n".join(lines)

    def show(self, parent: Optional[tk.Misc] = None) -> None:
        """
        Optional Tk viewer for the log. Safe to call even without a full GUI.
        """
        top = tk.Toplevel(parent) if parent is not None else tk.Toplevel()
        top.title("Parse Log")
        top.geometry("800x500")
        txt = tk.Text(top, wrap='word', font=("Courier New", 9))
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert('1.0', self.summary_text())
        txt.configure(state='disabled')


# ---------------------------------------------------------------------------
# 4) FileLoader
# ---------------------------------------------------------------------------

class FileLoader:
    """
    FileLoader centralizes file validation and ingestion for CSV/TSV/TXT/Excel.

    Responsibilities
    ----------------
    - Validate input files (exists, size, extension).
    - Detect CSV-like delimiters robustly.
    - Load CSV/TSV/TXT using Python csv (safe for all envs).
    - Load large CSVs using pandas in chunks (if available) with a progress callback.
    - Load Excel (XLSX/XLS) via pandas (requires openpyxl engine for .xlsx).
    - Clean and normalize headers/rows (strings, empty for NaN/None).
    - Provide header scoring to auto-pick the “best” Excel sheet.

    Outputs
    -------
    All loaders return a tuple: (headers: List[str], rows: List[List[str]])

    Notes
    -----
    - If pandas is missing, chunked loading falls back to the standard loader.
    - Errors are logged via the provided ParseLogger instance.
    """

    # Heuristic role synonyms copied from the legacy code for sheet/header scoring
    ROLE_SYNONYMS: Dict[str, List[str]] = {
        "Config Name": ["config name", "configname", "config_name", "cfg name", "cfgname", "cfg_name"],
        "Config Key":  ["config key", "cfg key", "config_key", "cfg_key", "key", "identifier", "id"],
        "CURRENT PAYLOAD": ["current payload", "current json", "new payload", "payload", "current", "new json", "json_payload"],
        "OLD PAYLOAD":     ["old payload", "old json", "previous payload", "previous json", "old"]
    }
    NEEDED_ROLES: Tuple[str, ...] = ("Config Name", "Config Key", "CURRENT PAYLOAD", "OLD PAYLOAD")

    def __init__(self, logger: Optional[ParseLogger] = None, max_file_mb: int = 1024) -> None:
        self.logger = logger or ParseLogger()
        self.max_file_mb = max(1, int(max_file_mb))  # safety floor

    # ---- Public API -----------------------------------------------------

    def validate_file(self, path: str) -> Tuple[bool, str]:
        """
        Check file presence, extension, and size.

        Returns
        -------
        (ok, reason)  -> ok=False with reason when invalid
        """
        if not os.path.exists(path):
            return False, "File not found."
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.csv', '.tsv', '.txt', '.xlsx', '.xls'):
            return False, f"Unsupported file type: {ext}"
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > self.max_file_mb:
                return False, f"File is too large ({size_mb:.1f} MB). Limit: {self.max_file_mb} MB."
        except OSError as e:
            return False, f"Cannot access file: {e}"
        return True, ""

    def load_csv(self, path: str) -> Tuple[List[str], List[List[str]]]:
        """
        Load a CSV/TSV/TXT file using Python's csv module with detected delimiter.
        """
        self._bump_csv_field_limit()
        delim = self._sniff_csv_delimiter(path)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                reader = csv.reader(f, delimiter=delim)
                try:
                    headers = [str(h) for h in next(reader)]
                except StopIteration:
                    self.logger.log("CSV file has no header row.", level='warning', context=os.path.basename(path))
                    return [], []
                rows: List[List[str]] = []
                for row in reader:
                    rows.append([str(x) if x is not None else '' for x in row])
                return headers, rows
        except Exception as e:
            self.logger.log(f"Failed to load CSV-like file: {e}", level='error', context=path)
            return [], []

    def load_chunked(
        self,
        path: str,
        chunk_size: int = 20_000,
        progress_cb: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[List[str], List[List[str]]]:
        """
        Load large CSV-like files in chunks using pandas (if available). Falls
        back to load_csv if pandas is unavailable or fails.

        Parameters
        ----------
        progress_cb : callable
            Called as progress_cb(percent_int, message)
        """
        if pd is None:
            self.logger.log("pandas not available; falling back to standard CSV loader.", level='warning')
            return self.load_csv(path)

        delim = self._sniff_csv_delimiter(path)
        try:
            try:
                file_size = os.path.getsize(path)
            except OSError:
                file_size = None

            headers: Optional[List[str]] = None
            all_rows: List[List[str]] = []

            chunks = pd.read_csv(
                path,
                dtype=str,
                chunksize=chunk_size,
                sep=delim,
                engine='python',
                on_bad_lines='skip',
                encoding='utf-8',
                encoding_errors='replace'
            )

            # Rough heuristic to estimate total chunks for a progress bar
            total_chunks = (file_size // (chunk_size * 100)) + 1 if file_size else 10

            for i, df in enumerate(chunks, 1):
                df = df.astype(str).fillna("")
                if headers is None:
                    headers = [str(c) for c in df.columns]
                all_rows.extend(df.values.tolist())
                if progress_cb:
                    step = min(100, int((i / max(1, total_chunks)) * 100))
                    progress_cb(step, f"Read ~{len(all_rows):,} rows")

            return headers or [], all_rows

        except Exception as e:
            self.logger.log(f"Chunked read failed ({e}); falling back to standard loader.", level='warning', context=path)
            return self.load_csv(path)

    def load_excel(self, path: str, sheet: Optional[str] = None) -> Tuple[List[str], List[List[str]]]:
        """
        Load headers/rows from an Excel file. If `sheet` is None, auto-pick the
        best sheet based on header scoring against NEEDED_ROLES.
        """
        if pd is None:
            self.logger.log("pandas is required to read Excel files.", level='error')
            return [], []

        try:
            book = pd.read_excel(path, sheet_name=None, dtype=str)
        except Exception as e:
            self.logger.log(f"Failed to read Excel file: {e}", level='error', context=path)
            return [], []

        if sheet:
            df = book.get(sheet)
            if df is None:
                self.logger.log(f"Sheet '{sheet}' not found in Excel.", level='error', context=os.path.basename(path))
                return [], []
            df = df.astype(str).fillna("")
            return [str(c) for c in df.columns], df.values.tolist()

        # Auto-pick best sheet by header score
        best_headers: List[str] = []
        best_rows: List[List[str]] = []
        best_score: float = -1.0
        best_name: Optional[str] = None

        for name, df in book.items():
            df = df.astype(str).fillna("")
            headers = [str(c) for c in df.columns]
            score = self._score_headers(headers)
            if score > best_score:
                best_score = score
                best_headers = headers
                best_rows = df.values.tolist()
                best_name = name

        if best_name is None:
            self.logger.log("No usable sheets detected in Excel file.", level='warning', context=os.path.basename(path))
        else:
            self.logger.log(f"Auto-selected sheet '{best_name}' (score={best_score:.2f})", level='warning')

        return best_headers, best_rows

    # ---- Column mapping helpers (kept for backward-compatibility) ------

    def detect_best_columns(self, headers: List[str]) -> Tuple[Dict[str, int], Dict[str, float]]:
        """
        For legacy compatibility: choose likely columns for required roles.

        Returns
        -------
        mapping: {role -> column_index}
        confidence: {role -> 0..1}
        """
        conf: Dict[str, float] = {}
        mapping: Dict[str, int] = {}
        used_indices = set()

        for role in self.NEEDED_ROLES:
            best_i, best_c = -1, -0.1
            for i, h in enumerate(headers):
                if i in used_indices:
                    continue
                c = self._header_confidence(h, role)
                if c > best_c:
                    best_c, best_i = c, i
            if best_i != -1 and best_c > 0.4:
                mapping[role] = best_i
                conf[role] = best_c
                used_indices.add(best_i)
        return mapping, conf

    def assemble_rows(self, headers: List[str], raw_rows: List[List[str]], mapping: Dict[str, int]) -> List[Dict[str, str]]:
        """
        Utility to convert rows+headers into a list of dicts keyed by the
        NEEDED_ROLES using the provided mapping. Unknown indices => empty string.
        """
        col_indices = {role: mapping.get(role, -1) for role in self.NEEDED_ROLES}
        rows: List[Dict[str, str]] = []
        for raw in raw_rows:
            row: Dict[str, str] = {}
            for role, idx in col_indices.items():
                row[role] = raw[idx] if 0 <= idx < len(raw) else ""
            rows.append(row)
        return rows

    # ---- Private utilities ---------------------------------------------

    @staticmethod
    def _bump_csv_field_limit() -> None:
        """
        Max out Python's CSV field size limit to better handle huge JSON cells.
        """
        try:
            csv.field_size_limit(sys.maxsize)
        except OverflowError:  # 32-bit Python
            csv.field_size_limit(2 ** 30)

    def _sniff_csv_delimiter(self, path: str) -> str:
        """
        Try to sniff delimiter; fall back to ',' and special-case .tsv.
        """
        default = ','
        ext = os.path.splitext(path)[1].lower()
        if ext == '.tsv':
            return '\t'
        try:
            with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                sample = f.read(8192)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=',\t;|')
                return dialect.delimiter
        except (csv.Error, UnicodeDecodeError) as e:
            self.logger.log(f"Delimiter sniff failed ({e}); using default ','.", level='warning', context=os.path.basename(path))
            return default

    # ---- Header scoring (sheet/column detection) -----------------------

    def _score_headers(self, headers: List[str]) -> float:
        """
        Sum the best confidence match for each needed role. Higher is better.
        """
        return sum(max(self._header_confidence(h, r) for h in headers) for r in self.NEEDED_ROLES) if headers else 0.0

    def _header_confidence(self, header: str, role: str) -> float:
        """
        Confidence score (0..1) that a header corresponds to a semantic role.
        """
        h = header.strip().lower()
        if not h:
            return 0.0
        syns = self.ROLE_SYNONYMS.get(role, [])
        direct_score = 0.0
        for s in syns:
            if h == s:
                return 1.0  # exact match
            if s in h:
                # proportional to coverage
                direct_score = max(direct_score, 0.6 + (0.4 * len(s) / len(h)))

        hint_score = 0.0
        if role == "Config Key" and ("key" in h or "id" in h):
            hint_score = 0.5
        if role == "Config Name" and "name" in h:
            hint_score = 0.5
        if role.endswith("PAYLOAD") and ("payload" in h or "json" in h):
            hint_score = 0.6
            if "current" in h and "CURRENT" in role:
                hint_score = 0.9
            if "new" in h and "CURRENT" in role:
                hint_score = 0.8
            if "old" in h and "OLD" in role:
                hint_score = 0.9
        return max(direct_score, hint_score)


# ---------------------------------------------------------------------------
# 5) Future placeholders (for next phases) — stubs only for now
# ---------------------------------------------------------------------------

class DiffEngine:  # placeholder
    """(Phase 2) DeepDiff integration and diff struct normalization."""
    pass


class PayloadFormatter:  # placeholder
    """(Phase 2) Pretty printing JSON + inline char-level diffs."""
    pass


class SummaryDashboard:  # placeholder
    """(Phase 2) Tkinter pivot dashboard & optional matplotlib chart."""
    pass


class SettingsManager:  # placeholder
    """(Phase 2) Persist default folder and other user preferences."""
    pass


class GUIController:  # placeholder
    """(Phase 3) Tkinter master app wiring everything together."""
    pass


# ---------------------------------------------------------------------------
# __main__ — simple CLI smoke test for FileLoader (no GUI required)
# ---------------------------------------------------------------------------

def _demo_cli() -> None:
    """
    Quick manual test:
        python PayloadAllInOne.py path/to/file.csv
        python PayloadAllInOne.py path/to/file.xlsx
    Prints header count, row count, and the first 2 rows.
    """
    if len(sys.argv) < 2:
        print("Usage: python PayloadAllInOne.py <file.csv|file.xlsx> [--chunked]")
        sys.exit(0)

    path = sys.argv[1]
    chunked = "--chunked" in sys.argv[2:]

    logger = ParseLogger()
    loader = FileLoader(logger=logger)

    ok, why = loader.validate_file(path)
    if not ok:
        print(f"[ERROR] {why}")
        sys.exit(2)

    ext = os.path.splitext(path)[1].lower()
    if ext in ('.csv', '.tsv', '.txt'):
        if chunked:
            print("[i] Using chunked loader...")
            headers, rows = loader.load_chunked(path, chunk_size=20000, progress_cb=lambda p, m: print(f"{p:3d}% {m}", end='\r'))
            print()  # newline after progress
        else:
            headers, rows = loader.load_csv(path)
    else:
        headers, rows = loader.load_excel(path)

    print(f"[OK] Headers: {len(headers)} | Rows: {len(rows)}")
    print("Headers:", headers)
    for i, r in enumerate(rows[:2]):
        print(f"Row {i+1}:", r)

    # Show any parse warnings
    if logger.entries:
        print("\n--- Parse Log ---")
        print(logger.summary_text())


if __name__ == "__main__":
    _demo_cli()
