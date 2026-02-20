# -*- coding: utf-8 -*-
"""
PayloadDiffViewerApp.py

A desktop UI (Tkinter) to compare CURRENT vs OLD JSON payloads
from CSV/TSV/TXT or Excel (XLSX/XLS), grouped by:
  - Config Name
  - Config Key

Features:
- Threaded loading with progress dialog (no UI freeze)
- Smart column detection with confirmation dialog
- Robust JSON parsing with parse log window
- DeepDiff engine (arrays-as-sets toggle)
- Diff table with filter + watchlist
- Inline (character-level) diff for selected field
- Full OLD/CURRENT JSON panes with BRIGHT YELLOW line highlight
- Export visible diffs to CSV and TXT (includes JSON fragments)
- Keyboard shortcuts: Ctrl+O / Ctrl+S / Ctrl+E / Ctrl+F / F5 / Esc

Enhancements (previous + this version):
- Synchronized vertical scrolling between full JSON panes (OLD and CURRENT).
  * Uses explicit references to the vertical scrollbars and Text widgets.
  * Fractions are mirrored; a small re-entrancy guard avoids recursion.
- Highlight the relevant line in BOTH panes (bright yellow, black text) and
  scroll both panes so the difference is visible.
  * Regex-based key + json-dumped value matching; key-only fallback for robustness.
- View â†’ Summary (Ctrl+M): Summary Dashboard
  * Pivot table: "Config Name | Count" (sortable by Count desc or by Name).
  * Optional bar chart if matplotlib is installed (TkAgg backend).
  * Export Summary CSV and Save Chart PNG (when matplotlib present).
- File â†’ Set Default Folderâ€¦ : Persist a default starting folder for "Openâ€¦"
  * Saved in ~/.payloaddiff_settings.json
  * Used as initialdir for open dialogs on startup.
"""

from __future__ import annotations

import os
import re
import csv
import ast
import sys
import json
import time
import queue
import threading
import difflib
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Dict, List, Tuple, Optional, Iterable
from urllib.parse import urlparse, parse_qs, unquote




# UI
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

# Data libs (pandas optional but recommended for large CSVs/Excel & pivot)
try:
    import pandas as pd
except ImportError:
    pd = None

# DeepDiff
from deepdiff import DeepDiff

# Optional pretty JSON library
try:
    import orjson
except ImportError:
    orjson = None

# Optional charting (Summary Dashboard)
HAS_MPL = False
try:
    import matplotlib
    matplotlib.use("TkAgg")  # Embed in Tk
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except Exception:
    HAS_MPL = False
    
    
def sharepoint_url_to_unc(url: str) -> Optional[str]:
    """
    Convert SharePoint/OneDrive folder URLs to a UNC/WebDAV path Windows understands.
    Supports:
      - https://<tenant>-my.sharepoint.com/personal/.../Documents/...
      - https://<tenant>.sharepoint.com/sites/<SiteName>/Shared%20Documents/...
      - https://<tenant>-my.sharepoint.com/my?id=/personal/.../Documents/...
    """
    try:
        u = urlparse(url.strip())
        if u.scheme not in ('http', 'https') or 'sharepoint.com' not in u.netloc:
            return None

        path = u.path
        # Handle "my?id=<encoded path>" style
        if path.rstrip('/').endswith('/my'):
            q = parse_qs(u.query or '')
            raw_id = (q.get('id') or [None])[0]
            if raw_id:
                path = raw_id  # it's already an absolute path like /personal/...
        # Normalize odd copy-link patterns like '/:f:/r/'
        path = str(path).replace('/:f:/r/', '/').strip('/')
        path = unquote(path)  # decode %20 etc.

        # Require a plausible library path
        if not (path.startswith('personal/') or path.startswith('sites/')):
            return None

        # UNC format: \\host@SSL\path-with-backslashes
        host = u.netloc
        return r"\\{host}@SSL\{path}".format(host=host, path=path.replace('/', '\\'))
    except Exception:
        return None
    
    


# ----------------------------
# Configuration / UI constants
# ----------------------------

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

    # Inline diff pane default heights (rows)
    INLINE_ROWS = 8

    # Row highlight colors
    COLOR_CHANGED = '#FFF5CC'  # amber (row background)
    COLOR_ADDED   = '#E6FFED'  # light green
    COLOR_REMOVED = '#FFECEC'  # light red

    # Strong line highlight (works on Windows light/dark)
    COLOR_LINE_HIT_BG = '#ffeb3b'
    COLOR_LINE_HIT_FG = 'black'
    
    # Default values
    DEFAULT_WATCHLIST = 'numericCurrencyCode, schemeConfigs, processingAgreements'
    DIFF_DISPLAY_LIMIT = 5000

    # Settings file
    SETTINGS_FILE = os.path.expanduser('~/.payloaddiff_settings.json')


# --------------------------------
# Logger for parse warnings/errors
# --------------------------------

class ParseLogger:
    """Lightweight parse logger with a Toplevel viewer."""
    def __init__(self):
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

    def show(self, parent: tk.Tk) -> None:
        top = tk.Toplevel(parent)
        top.title("Parse Log")
        top.geometry("800x500")
        txt = tk.Text(top, wrap='word', font=("Courier New", 9))
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert('1.0', self.summary_text())
        txt.configure(state='disabled')


# --------------------------
# Helpers: JSON + Deep paths
# --------------------------

TRAILING_COMMAS = re.compile(r',\s*([}\]])')

def parse_jsonish_verbose(s: str) -> Tuple[Any, str]:
    """
    Return (parsed_obj, error_message_if_any).
    Tries strict JSON -> trailing-comma fix -> ast.literal_eval
    """
    t = (s or '').strip()
    if not t:
        return None, "Empty payload"

    # Strict JSON
    try:
        return json.loads(t), ""
    except JSONDecodeError:
        pass

    # Remove trailing commas
    try:
        t2 = TRAILING_COMMAS.sub(r'\1', t)
        return json.loads(t2), ""
    except JSONDecodeError:
        pass

    # Python literal
    try:
        return ast.literal_eval(t), ""
    except (ValueError, SyntaxError, TypeError) as e:
        return None, f"Failed to parse payload ({e.__class__.__name__})"


def pretty_json(obj: Any) -> str:
    if obj is None:
        return ""
    try:
        if orjson is not None:
            # orjson is faster and handles more types
            return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode()
    except Exception:
        pass
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def dd_path_to_key(p: str) -> str:
    """
    DeepDiff path "root['a'][2]['b']" -> "a[2].b"
    """
    if not p:
        return ""
    p = p.replace("root", "")
    p = re.sub(r"\['([^']*)'\]", r".\1", p) # Handle empty strings in keys
    p = re.sub(r"\[(\d+)\]", r"[\1]", p) # Keep numeric indices as is
    p = p.lstrip('.')
    return p


def _path_tokens(path: str) -> List[str]:
    """
    Turn "a[2].b.c[10]" into tokens: ['a', '[2]', 'b', 'c', '[10]']
    """
    return [tok for tok in re.split(r'\.|(\[\d+\])', path) if tok]


def value_from_path(obj: Any, dd_path: str) -> Any:
    """
    Try to fetch value from obj following DeepDiff path string.
    dd_path: "root['a'][2]['b']"
    """
    dotted = dd_path_to_key(dd_path)  # "a[2].b"
    toks = _path_tokens(dotted)
    cur = obj
    try:
        for t in toks:
            if t.startswith('[') and t.endswith(']'):
                idx = int(t[1:-1])
                cur = cur[idx]
            else:
                cur = cur[t]
        return cur
    except (KeyError, IndexError, TypeError):
        return None


def build_fragment_from_path_value(path: str, value: Any) -> Any:
    """
    Make a minimal JSON fragment showing the the leaf at `path` with `value`.
    Example: path="a.b[2].c"  => {"a":{"b":[null,null,{"c": value}]}}
    """
    tokens = _path_tokens(path)
    if not tokens:
        return value

    # Create the structure backwards from the value
    fragment = value
    for tok in reversed(tokens):
        if tok.startswith('[') and tok.endswith(']'):
            idx = int(tok[1:-1])
            new_list = [None] * (idx + 1)
            new_list[idx] = fragment
            fragment = new_list
        else:
            fragment = {tok: fragment}
    return fragment


# ---------------------------------
# File reading helpers (CSV/Excel)
# ---------------------------------

def _bump_csv_field_limit():
    try:
        # Set limit to the maximum possible value for the platform
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        # Fallback for platforms with limitations (e.g., 32-bit Windows)
        csv.field_size_limit(2**30)


def _sniff_csv_delimiter(path: str) -> str:
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
    except (csv.Error, UnicodeDecodeError):
        return default


def _load_csv_like_headers_rows(path: str) -> Tuple[List[str], List[List[str]]]:
    _bump_csv_field_limit()
    delim = _sniff_csv_delimiter(path)
    with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
        reader = csv.reader(f, delimiter=delim)
        try:
            headers = [str(h) for h in next(reader)]
        except StopIteration:
            return [], []
        rows: List[List[str]] = []
        for row in reader:
            rows.append([str(x) if x is not None else '' for x in row])
        return headers, rows


def _load_csv_like_headers_rows_chunked(path: str, chunk_size: int = 20000,
                                        progress_cb: Optional[callable] = None) -> Tuple[List[str], List[List[str]]]:
    if pd is None:
        return _load_csv_like_headers_rows(path)

    delim = _sniff_csv_delimiter(path)
    try:
        file_size = os.path.getsize(path)
    except OSError:
        file_size = None

    headers = None
    all_rows: List[List[str]] = []

    try:
        # Use pandas for robust, chunked reading
        chunks = pd.read_csv(path, dtype=str, chunksize=chunk_size,
                             sep=delim, engine='python', on_bad_lines='skip',
                             encoding='utf-8', encoding_errors='replace')
        
        # Estimate total chunks for progress bar
        total_chunks = (file_size // (chunk_size * 100)) + 1 if file_size else 10  # Rough heuristic
        
        for i, chunk in enumerate(chunks, 1):
            if headers is None:
                headers = [str(c) for c in chunk.columns]
            chunk = chunk.astype(str).fillna("")
            all_rows.extend(chunk.values.tolist())

            if progress_cb:
                step = min(100, int((i / max(1, total_chunks)) * 100))
                progress_cb(step, f"Read ~{len(all_rows):,} rows")
                
    except Exception as e:
        # Fallback if pandas fails for any reason
        if progress_cb:
            progress_cb(50, f"Pandas failed ({e}), falling back...")
        return _load_csv_like_headers_rows(path)

    return headers or [], all_rows


def _excel_headers_rows(path: str, sheet: Optional[str] = None) -> Tuple[List[str], List[List[str]]]:
    if pd is None:
        raise RuntimeError("pandas is required to read Excel files")

    try:
        book = pd.read_excel(path, sheet_name=None, dtype=str)
    except Exception as e:
        raise RuntimeError(f"Failed to read Excel file: {e}") from e

    if sheet:
        df = book.get(sheet)
        if df is None:
            raise ValueError(f"Sheet '{sheet}' not found in the Excel file.")
        df = df.astype(str).fillna("")
        return [str(c) for c in df.columns], df.values.tolist()

    # If no sheet is specified, find the best one based on header content
    best_headers, best_rows, best_score = [], [], -1.0
    for _, df in book.items():
        df = df.astype(str).fillna("")
        headers = [str(c) for c in df.columns]
        score = _score_headers(headers)
        if score > best_score:
            best_score, best_headers, best_rows = score, headers, df.values.tolist()

    return best_headers, best_rows


# --------------------------
# Column detection / mapping
# --------------------------

ROLE_SYNONYMS = {
    "Config Name": ["config name", "configname", "config_name", "cfg name", "cfgname", "cfg_name"],
    "Config Key":  ["config key", "cfg key", "config_key", "cfg_key", "key", "identifier", "id"],
    "CURRENT PAYLOAD": ["current payload", "current json", "new payload", "payload", "current", "new json", "json_payload"],
    "OLD PAYLOAD":     ["old payload", "old json", "previous payload", "previous json", "old"]
}

NEEDED_ROLES = ["Config Name", "Config Key", "CURRENT PAYLOAD", "OLD PAYLOAD"]

def _header_confidence(header: str, role: str) -> float:
    h = header.strip().lower()
    if not h: return 0.0
    
    syns = ROLE_SYNONYMS.get(role, [])
    direct_score = 0.0
    for s in syns:
        if h == s:
            return 1.0  # Exact match is best
        if s in h:
            # Score based on how much of the header is the synonym
            direct_score = max(direct_score, 0.6 + (0.4 * len(s) / len(h)))

    # Weak hints
    hint_score = 0.0
    if role == "Config Key" and ("key" in h or "id" in h):
        hint_score = 0.5
    if role == "Config Name" and "name" in h:
        hint_score = 0.5
    if role.endswith("PAYLOAD") and ("payload" in h or "json" in h):
        hint_score = 0.6
        if "current" in h and "CURRENT" in role: hint_score = 0.9
        if "new" in h and "CURRENT" in role:    hint_score = 0.8
        if "old" in h and "OLD" in role:        hint_score = 0.9

    return max(direct_score, hint_score)


def _score_headers(headers: List[str]) -> float:
    # How many of the needed roles are confidently present?
    return sum(max(_header_confidence(h, r) for h in headers) for r in NEEDED_ROLES)


def detect_best_columns(headers: List[str]) -> Tuple[Dict[str, int], Dict[str, float]]:
    """
    Return (mapping, confidence_per_role)
      mapping: {role: column_index}
    """
    conf: Dict[str, float] = {}
    mapping: Dict[str, int] = {}
    used_indices = set()

    # Iterate roles and find the best unique column for each
    for role in NEEDED_ROLES:
        best_i, best_c = -1, -0.1
        for i, h in enumerate(headers):
            if i in used_indices:
                continue
            c = _header_confidence(h, role)
            if c > best_c:
                best_c, best_i = c, i
        
        if best_i != -1 and best_c > 0.4:  # Confidence threshold
            mapping[role] = best_i
            conf[role] = best_c
            used_indices.add(best_i)
            
    return mapping, conf


def assemble_rows(headers: List[str], raw_rows: List[List[str]], mapping: Dict[str, int]) -> List[Dict[str, str]]:
    col_indices = {role: mapping.get(role, -1) for role in NEEDED_ROLES}
    rows: List[Dict[str, str]] = []
    
    for raw in raw_rows:
        row = {}
        for role, idx in col_indices.items():
            row[role] = raw[idx] if 0 <= idx < len(raw) else ""
        rows.append(row)
        
    return rows


# ----------------------------
# Diff row structure / metadata
# ----------------------------

@dataclass
class RowMeta:
    cfgkey: str
    typ: str        # 'changed' / 'added' / 'removed'
    path: str       # dotted path, e.g., a[2].b
    old: Any
    new: Any
    old_obj: Any
    new_obj: Any


# ----------------------------
# The main application class
# ----------------------------

class PayloadDiffViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Payload Diff Viewer (Config Name -> Current vs Old)")
        self.geometry(f"{UIConfig.WINDOW_W}x{UIConfig.WINDOW_H}")
        self.minsize(UIConfig.MIN_W, UIConfig.MIN_H)

        # Settings & paths
        self.settings: Dict[str, Any] = {}
        self._last_open_dir: Optional[str] = None
        self._load_settings()

        # State
        self.rows: List[Dict[str, str]] = []
        self.by_name: Dict[str, List[Dict[str, str]]] = {}
        self.parse_logger = ParseLogger()

        # Watch & filter
        self.watchlist: List[str] = []
        self.only_watch = tk.BooleanVar(value=False)
        self.arrays_as_sets = tk.BooleanVar(value=False)

        # UI bits
        self._tree_meta: Dict[str, RowMeta] = {}
        self._row_order: Dict[str, int] = {}
        self.search_var = tk.StringVar()

        # Scroll sync guard for full JSON panes
        self._scroll_sync_active = False

        # Build UI and shortcuts
        self._build_ui()
        self._bind_shortcuts()

    # ------------- Settings persistence -------------

    def _load_settings(self):
        """Load settings from ~/.payloaddiff_settings.json. Create file if missing."""
        path = UIConfig.SETTINGS_FILE
        # Create file if it doesn't exist
        if not os.path.exists(path):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.settings = json.load(f) or {}
        except Exception:
            self.settings = {}

    def _save_settings(self):
        """Save settings to ~/.payloaddiff_settings.json."""
        try:
            with open(UIConfig.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showwarning("Settings", f"Failed to save settings:\n{e}")

    def _get_initial_open_dir(self) -> Optional[str]:
        d = self.settings.get('default_open_dir')
        if d:
            if d.lower().startswith('http'):
                # Convert SharePoint URL â†’ UNC and use it if reachable
                unc = sharepoint_url_to_unc(d)
                if unc and os.path.isdir(unc):
                    return unc
                # If not reachable yet (auth not established), fall through
            elif os.path.isdir(d):
                return d

        if self._last_open_dir and os.path.isdir(self._last_open_dir):
            return self._last_open_dir
        return None

    def _set_default_folder(self):
        """File â†’ Set Default Folderâ€¦ action."""
        initial = self._get_initial_open_dir() or os.path.expanduser('~')
        folder = filedialog.askdirectory(title="Choose Default Open Folder", initialdir=initial)
        if not folder:
            return
        try:
            self.settings['default_open_dir'] = folder
            self._save_settings()
            messagebox.showinfo("Default Folder", f"Default open folder set to:\n{folder}")
        except Exception as e:
            messagebox.showerror("Default Folder", f"Failed to set default folder:\n{e}")

    # ------------- UI --------------

    def _build_ui(self):
        # Menu
        menubar = tk.Menu(self)

        # File menu
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Openâ€¦ (Ctrl+O)", command=self.on_open)
        filemenu.add_separator()
        filemenu.add_command(label="Set Default Folderâ€¦", command=self._set_default_folder)
        filemenu.add_separator()
        filemenu.add_command(label="Export CSV (Ctrl+S)", command=self.on_export_csv)
        filemenu.add_command(label="Export TXT (Ctrl+E)", command=self.on_export_txt)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        # View menu
        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label="Summary (Ctrl+M)", command=self.on_view_summary)
        menubar.add_cascade(label="View", menu=viewmenu)

        # Help menu
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Show Parse Log", command=lambda: self.parse_logger.show(self))
        helpmenu.add_separator()
        helpmenu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts_help)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.config(menu=menubar)

        # Top controls
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(top, text='Openâ€¦', command=self.on_open).pack(side=tk.LEFT)

        ttk.Label(top, text='Config Name:').pack(side=tk.LEFT, padx=(12, 4))
        self.cmb_name = ttk.Combobox(top, state='disabled', width=36)
        self.cmb_name.pack(side=tk.LEFT)
        self.cmb_name.bind('<<ComboboxSelected>>', self.on_name_selected)

        ttk.Label(top, text='Config Keys:').pack(side=tk.LEFT, padx=(12, 4))
        self.lst_keys = tk.Listbox(top, selectmode=tk.EXTENDED, width=38, height=6, exportselection=False)
        self.lst_keys.pack(side=tk.LEFT)
        self.lst_keys.configure(state=tk.DISABLED)

        # Vertical button frame
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.LEFT, padx=(12,0), fill=tk.Y)
        self.btn_compare = ttk.Button(btn_frame, text='Compare (F5)', state='disabled', command=self.on_compare)
        self.btn_compare.pack(pady=(0,2))
        self.btn_clear = ttk.Button(btn_frame, text='Clear Results', state='disabled', command=self._reset_views)
        self.btn_clear.pack()

        # Export buttons
        self.btn_export_csv = ttk.Button(top, text='Export CSV', state='disabled', command=self.on_export_csv)
        self.btn_export_csv.pack(side=tk.LEFT, padx=(6, 0))
        self.btn_export_txt = ttk.Button(top, text='Export TXT', state='disabled', command=self.on_export_txt)
        self.btn_export_txt.pack(side=tk.LEFT, padx=(6, 0))

        # Status label
        self.lbl = ttk.Label(self, text='Open a CSV/Excel file to begin.')
        self.lbl.pack(anchor='w', padx=12)

        # Options row (arrays mode, watchlist)
        opt = ttk.Frame(self)
        opt.pack(fill=tk.X, padx=10, pady=(2, 6))

        ttk.Label(opt, text='Arrays:').pack(side=tk.LEFT)
        ttk.Radiobutton(opt, text='by index', variable=self.arrays_as_sets, value=False, command=self.on_compare).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Radiobutton(opt, text='as set (ignore order)', variable=self.arrays_as_sets, value=True, command=self.on_compare).pack(side=tk.LEFT)

        ttk.Label(opt, text='  Watch keys:').pack(side=tk.LEFT, padx=(14, 4))
        self.ent_watch = ttk.Entry(opt, width=64)
        self.ent_watch.pack(side=tk.LEFT)
        self.ent_watch.insert(0, UIConfig.DEFAULT_WATCHLIST)
        ttk.Checkbutton(opt, text='Only watch', variable=self.only_watch, command=self._filter_tree).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(opt, text='Apply', command=self.apply_watchlist).pack(side=tk.LEFT, padx=(8, 0))

        # Filter row + counts
        flt = ttk.Frame(self)
        flt.pack(fill=tk.X, padx=10, pady=(0, 6))
        ttk.Label(flt, text='Filter:').pack(side=tk.LEFT)
        self.filter_entry = ttk.Entry(flt, textvariable=self.search_var, width=40)
        self.filter_entry.pack(side=tk.LEFT, padx=8)
        ttk.Button(flt, text='Clear', command=lambda: self.search_var.set('')).pack(side=tk.LEFT)
        self.search_var.trace_add('write', lambda *_: self._filter_tree())

        self.v_changed = tk.StringVar(value='Changed: 0')
        self.v_added   = tk.StringVar(value='Added: 0')
        self.v_removed = tk.StringVar(value='Removed: 0')
        ttk.Label(flt, textvariable=self.v_changed, foreground='#7a5a00').pack(side=tk.LEFT, padx=(20, 12))
        ttk.Label(flt, textvariable=self.v_added, foreground='#096b00').pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(flt, textvariable=self.v_removed, foreground='#a00000').pack(side=tk.LEFT)

        # Diff table
        ftable = ttk.Frame(self)
        ftable.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 8))

        self.tree = ttk.Treeview(ftable, columns=UIConfig.TREE_COLUMNS, show='headings', selectmode='browse')
        for c in UIConfig.TREE_COLUMNS:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=UIConfig.TREE_WIDTHS[c], anchor='w')
        vsb = ttk.Scrollbar(ftable, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(ftable, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        ftable.rowconfigure(0, weight=1)
        ftable.columnconfigure(0, weight=1)

        # Row color tags
        self.tree.tag_configure('changed', background=UIConfig.COLOR_CHANGED)
        self.tree.tag_configure('added',   background=UIConfig.COLOR_ADDED)
        self.tree.tag_configure('removed', background=UIConfig.COLOR_REMOVED)

        # Watch tag
        default_font = tkfont.nametofont("TkDefaultFont")
        bold_font = tkfont.Font(**default_font.configure())
        bold_font.configure(weight='bold')
        self.tree.tag_configure('watch', foreground='#0b5bb5', font=bold_font)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # Lower panes: inline diff | full JSONs
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Inline diff panel
        fmid = ttk.LabelFrame(paned, text='Selected Field - Inline Diff')
        paned.add(fmid, weight=1)

        left = ttk.Frame(fmid)
        left.grid(row=1, column=0, sticky='nsew', padx=(0, 6))
        right = ttk.Frame(fmid)
        right.grid(row=1, column=1, sticky='nsew', padx=(6, 0))
        fmid.columnconfigure(0, weight=1)
        fmid.columnconfigure(1, weight=1)
        fmid.rowconfigure(1, weight=1)

        ttk.Label(left, text='OLD').pack(anchor='w')
        self.txt_sel_old = tk.Text(left, wrap='word', height=UIConfig.INLINE_ROWS, font=("Courier New", 9))
        self.txt_sel_old.pack(fill=tk.BOTH, expand=True)
        self.txt_sel_old.tag_configure('del', background='#ffcccc')

        ttk.Label(right, text='CURRENT').pack(anchor='w')
        self.txt_sel_new = tk.Text(right, wrap='word', height=UIConfig.INLINE_ROWS, font=("Courier New", 9))
        self.txt_sel_new.pack(fill=tk.BOTH, expand=True)
        self.txt_sel_new.tag_configure('add', background='#c2f0c2')

        # Full JSONs (synchronized vertical scrolling)
        fbot = ttk.Frame(paned)
        paned.add(fbot, weight=2)

        jl = ttk.LabelFrame(fbot, text='OLD Payload (Full JSON)')
        jl.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        jr = ttk.LabelFrame(fbot, text='CURRENT Payload (Full JSON)')
        jr.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        fbot.columnconfigure(0, weight=1)
        fbot.columnconfigure(1, weight=1)
        fbot.rowconfigure(0, weight=1)

        # Text widgets
        self.txt_old = tk.Text(jl, wrap='none', font=("Courier New", 9))
        self.txt_cur = tk.Text(jr, wrap='none', font=("Courier New", 9))

        # Explicit scrollbars (vertical + horizontal)
        self.sc_old_y = ttk.Scrollbar(jl, orient='vertical')
        self.sc_old_x = ttk.Scrollbar(jl, orient='horizontal')
        self.sc_cur_y = ttk.Scrollbar(jr, orient='vertical')
        self.sc_cur_x = ttk.Scrollbar(jr, orient='horizontal')

        # Place widgets
        self.txt_old.pack(fill=tk.BOTH, expand=True)
        self.sc_old_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.sc_old_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.txt_cur.pack(fill=tk.BOTH, expand=True)
        self.sc_cur_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.sc_cur_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure scroll commands (horizontal independent)
        self.txt_old.configure(xscrollcommand=self.sc_old_x.set)
        self.txt_cur.configure(xscrollcommand=self.sc_cur_x.set)
        self.sc_old_x.configure(command=self.txt_old.xview)
        self.sc_cur_x.configure(command=self.txt_cur.xview)

        # -------- Synchronized vertical scrolling wiring --------
        # We wire both Text widgets to a yscrollcommand callback that:
        #   - updates BOTH scrollbars' set() to keep them visually consistent
        #   - mirrors the fractional position to the other Text via yview_moveto()
        # And both vertical scrollbars' command() scroll BOTH Text widgets.
        # A small re-entrancy guard avoids infinite recursion.
        self.txt_old.configure(
            yscrollcommand=lambda first, last: self._on_yscroll(self.txt_old, self.txt_cur,
                                                                self.sc_old_y, self.sc_cur_y, first, last)
        )
        self.txt_cur.configure(
            yscrollcommand=lambda first, last: self._on_yscroll(self.txt_cur, self.txt_old,
                                                                self.sc_cur_y, self.sc_old_y, first, last)
        )

        self.sc_old_y.configure(
            command=lambda *args: self._on_scrollbar_y(self.txt_old, self.txt_cur,
                                                       self.sc_old_y, self.sc_cur_y, *args)
        )
        self.sc_cur_y.configure(
            command=lambda *args: self._on_scrollbar_y(self.txt_cur, self.txt_old,
                                                       self.sc_cur_y, self.sc_old_y, *args)
        )
        # --------------------------------------------------------

    def _bind_shortcuts(self):
        self.bind_all('<Control-o>', lambda e: self.on_open())
        self.bind_all('<Control-s>', lambda e: self.on_export_csv())
        self.bind_all('<Control-e>', lambda e: self.on_export_txt())
        self.bind_all('<Control-f>', lambda e: (self.filter_entry.focus_set(), self.filter_entry.select_range(0, tk.END)))
        self.bind_all('<Control-m>', lambda e: self.on_view_summary())
        self.bind_all('<F5>', lambda e: self.on_compare())
        self.bind_all('<Escape>', lambda e: self.focus_set())

    # ------------- Actions -------------

    def _validate_file(self, path: str) -> Tuple[bool, str]:
        if not os.path.exists(path):
            return False, "File not found."
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.csv', '.tsv', '.txt', '.xlsx', '.xls'):
            return False, f"Unsupported file type: {ext}"
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > 1024:  # 1 GB limit
                return False, f"File is too large ({size_mb:.1f} MB)."
        except OSError as e:
            return False, f"Cannot access file: {e}"
        return True, ""

    def on_open(self):
        p = filedialog.askopenfilename(
            title="Select CSV/TSV/TXT/XLSX/XLS",
            initialdir=self._get_initial_open_dir(),
            filetypes=[
                ("All supported", "*.csv *.tsv *.txt *.xlsx *.xls"),
                ("Excel", "*.xlsx *.xls"),
                ("CSV/TSV/TXT", "*.csv *.tsv *.txt"),
                ("All files", "*.*"),
            ]
        )
        if not p:
            return

        self._last_open_dir = os.path.dirname(p) or self._last_open_dir

        ok, why = self._validate_file(p)
        if not ok:
            messagebox.showerror("File Error", why)
            return

        ext = os.path.splitext(p)[1].lower()
        use_chunked = (pd is not None) and (ext in ('.csv', '.tsv', '.txt'))

        def load_task(progress_cb=None):
            if ext in ('.csv', '.tsv', '.txt'):
                return _load_csv_like_headers_rows_chunked(p, progress_cb=progress_cb) if use_chunked else _load_csv_like_headers_rows(p)
            elif ext in ('.xlsx', '.xls'):
                try:
                    return _excel_headers_rows(p)
                except Exception as e:
                    raise
            raise ValueError("Unsupported file type should have been caught earlier.")

        def on_loaded(result):
            headers, raw_rows = result
            if not headers or not raw_rows:
                messagebox.showwarning('No Data', 'File appears to be empty or has no data rows.')
                return

            mapping, conf = detect_best_columns(headers)
            missing = [r for r in NEEDED_ROLES if r not in mapping]
            if missing:
                mapping2 = self._confirm_column_mapping(headers, mapping, conf)
                if not mapping2:
                    messagebox.showinfo("Cancelled", "Column mapping was not confirmed.")
                    return
                mapping = mapping2

            self.rows = assemble_rows(headers, raw_rows, mapping)
            self._finalize_load()

        self._with_progress_threaded(
            load_task,
            title=("Loading large file..." if use_chunked else "Loading file..."),
            done_cb=on_loaded,
            determinate=use_chunked
        )

    def _finalize_load(self):
        self.by_name.clear()
        self.parse_logger = ParseLogger()  # Reset logger for new file

        for r in self.rows:
            nm = (r.get('Config Name') or '').strip()
            if nm:
                self.by_name.setdefault(nm, []).append(r)

        names = sorted(self.by_name.keys())
        self.cmb_name.configure(state='readonly', values=names)
        self.cmb_name.set('')
        self.lst_keys.delete(0, tk.END)
        self.lst_keys.configure(state=tk.DISABLED)

        self.btn_compare.configure(state='disabled')
        self.btn_clear.configure(state='disabled')
        self.btn_export_csv.configure(state='disabled')
        self.btn_export_txt.configure(state='disabled')

        self.lbl.configure(text=f"Loaded {len(self.rows):,} rows. Select a Config Name to begin.")
        self._reset_views()

    def on_name_selected(self, _evt=None):
        n = self.cmb_name.get().strip()
        self._reset_views()
        self.btn_compare.configure(state='disabled')
        
        self.lst_keys.delete(0, tk.END)
        if not n:
            self.lst_keys.configure(state=tk.DISABLED)
            return

        keys = sorted({r['Config Key'].strip() for r in self.by_name.get(n, []) if r.get('Config Key', '').strip()})
        
        for k in keys:
            self.lst_keys.insert(tk.END, k)
            
        if keys:
            self.lst_keys.configure(state=tk.NORMAL)
            self.lst_keys.select_set(0, tk.END)  # Select all by default
            self.btn_compare.configure(state='normal')
        else:
            self.lst_keys.configure(state=tk.DISABLED)

    # ------------- Comparison Logic (Correct, set-safe) -------------

    def on_compare(self):
        """Orchestrates the UI and logic for comparing selected payloads."""
        name = self.cmb_name.get().strip()
        selected_keys = self._get_selected_config_keys()
        if not name or not selected_keys:
            return

        selected_path = self._get_selected_diff_path()

        rows_to_compare = self._get_rows_for_keys(name, selected_keys)
        diffs, stats = self._compute_all_diffs(rows_to_compare, name)

        if len(diffs) > UIConfig.DIFF_DISPLAY_LIMIT:
            msg = (f"The comparison generated {len(diffs):,} differences. "
                   f"Displaying them all may slow down the UI.\n\n"
                   f"Do you want to display only the first {UIConfig.DIFF_DISPLAY_LIMIT:,} results?")
            if messagebox.askyesno("Large Result Set", msg):
                diffs = diffs[:UIConfig.DIFF_DISPLAY_LIMIT]
            else:
                return

        self.v_changed.set(f"Changed: {stats['changed']}")
        self.v_added.set(f"Added: {stats['added']}")
        self.v_removed.set(f"Removed: {stats['removed']}")

        self._populate_table(diffs)
        self._try_restore_selection(selected_path)

        self.btn_clear.configure(state='normal')
        self.btn_export_csv.configure(state='normal')
        self.btn_export_txt.configure(state='normal')

    def _get_selected_config_keys(self) -> List[str]:
        """Retrieves the list of selected keys from the listbox."""
        sel_indices = self.lst_keys.curselection()
        if not sel_indices:
            messagebox.showwarning('Select Keys', 'Please select one or more Config Keys to compare.')
            return []
        return [self.lst_keys.get(i) for i in sel_indices]

    def _get_rows_for_keys(self, name: str, keys: List[str]) -> Iterable[Dict[str, str]]:
        """Filters relevant data rows for the selected keys."""
        rows = [r for r in self.by_name.get(name, []) if r.get('Config Key', '').strip() in keys]
        return rows

    def _compute_all_diffs(self, rows_to_compare: Iterable[Dict[str, str]], name: str) -> Tuple[List[RowMeta], Dict[str, int]]:
        """
        Computes differences and returns diffs list and stats.

        Important correctness: DeepDiff returns sets for some keys (e.g., dictionary_item_added/removed),
        not dicts. We handle each category appropriately and safely derive values when only a path is given.
        """
        all_diffs: List[RowMeta] = []
        stats = {'changed': 0, 'added': 0, 'removed': 0}
        ignore_order = self.arrays_as_sets.get()

        for row in rows_to_compare:
            k = row['Config Key']
            old_obj, err1 = parse_jsonish_verbose(row['OLD PAYLOAD'])
            cur_obj, err2 = parse_jsonish_verbose(row['CURRENT PAYLOAD'])
            if err1: self.parse_logger.log(f"[{name}/{k}] OLD: {err1}", context=row['OLD PAYLOAD'][:200])
            if err2: self.parse_logger.log(f"[{name}/{k}] CURRENT: {err2}", context=row['CURRENT PAYLOAD'][:200])

            try:
                dd = DeepDiff(old_obj, cur_obj, ignore_order=ignore_order, verbose_level=2)
            except Exception as e:
                self.parse_logger.log(f"[{name}/{k}] DeepDiff failed: {e}", level='error')
                continue

            # values/type changes (dicts)
            for path, change in dd.get('values_changed', {}).items():
                all_diffs.append(RowMeta(k, 'changed', dd_path_to_key(path), change.get('old_value'), change.get('new_value'), old_obj, cur_obj))
                stats['changed'] += 1
            for path, change in dd.get('type_changes', {}).items():
                all_diffs.append(RowMeta(k, 'changed', dd_path_to_key(path), change.get('old_value'), change.get('new_value'), old_obj, cur_obj))
                stats['changed'] += 1

            # added/removed in dictionaries (sets of deep paths)
            for path in dd.get('dictionary_item_added', set()):
                p = dd_path_to_key(path)
                val = value_from_path(cur_obj, path)  # now present in CURRENT
                all_diffs.append(RowMeta(k, 'added', p, None, val, old_obj, cur_obj))
                stats['added'] += 1

            for path in dd.get('dictionary_item_removed', set()):
                p = dd_path_to_key(path)
                val = value_from_path(old_obj, path)  # existed in OLD
                all_diffs.append(RowMeta(k, 'removed', p, val, None, old_obj, cur_obj))
                stats['removed'] += 1

            # iterables: added/removed are dicts path->value
            for path, val in dd.get('iterable_item_added', {}).items():
                all_diffs.append(RowMeta(k, 'added', dd_path_to_key(path), None, val, old_obj, cur_obj))
                stats['added'] += 1
            for path, val in dd.get('iterable_item_removed', {}).items():
                all_diffs.append(RowMeta(k, 'removed', dd_path_to_key(path), val, None, old_obj, cur_obj))
                stats['removed'] += 1

            # attribute-level diffs (rare; for objects with attributes)
            for path in dd.get('attribute_added', set()):
                p = dd_path_to_key(path)
                val = value_from_path(cur_obj, path)
                all_diffs.append(RowMeta(k, 'added', p, None, val, old_obj, cur_obj))
                stats['added'] += 1
            for path in dd.get('attribute_removed', set()):
                p = dd_path_to_key(path)
                val = value_from_path(old_obj, path)
                all_diffs.append(RowMeta(k, 'removed', p, val, None, old_obj, cur_obj))
                stats['removed'] += 1

        # Make table stable and readable
        typ_order = {'changed': 0, 'added': 1, 'removed': 2}
        all_diffs.sort(key=lambda m: (m.cfgkey, typ_order.get(m.typ, 9), m.path))
        return all_diffs, stats


    def _populate_table(self, diffs: List[RowMeta]):
        self.tree.delete(*self.tree.get_children())
        self._tree_meta.clear()
        self._row_order.clear()

        for idx, meta in enumerate(diffs):
            tags = [meta.typ]
            if self._row_is_watched(meta.path):
                tags.append('watch')
            iid = self.tree.insert('', tk.END, values=(meta.cfgkey, meta.typ, meta.path, self._s(meta.old), self._s(meta.new)), tags=tuple(tags))
            self._tree_meta[iid] = meta
            self._row_order[iid] = idx

        self._filter_tree()
        if not self.tree.selection():
            children = self.tree.get_children()
            if children:
                self.tree.selection_set(children[0])
                self.tree.focus(children[0])
                self.tree.see(children[0])

    def on_tree_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel: return
        meta = self._tree_meta.get(sel[0])
        if not meta: return

        # Inline diff for the selected scalar/text values
        self._show_inline_diff(
            str(meta.old if meta.old is not None else ""),
            str(meta.new if meta.new is not None else "")
        )

        # Render full JSONs
        self._render_full_payloads(meta.old_obj, meta.new_obj)

        # Highlight in BOTH panes and ensure both are scrolled to visibility.
        leaf_key = meta.path.split('.')[-1].split('[')[0] if meta.path else ''
        # Temporarily suppress scroll mirroring while we 'see' specific lines in each pane.
        self._scroll_sync_active = True
        try:
            self._highlight_line_for_key_value(self.txt_old, leaf_key, meta.old)
            self._highlight_line_for_key_value(self.txt_cur, leaf_key, meta.new)
        finally:
            self._scroll_sync_active = False

    # ------------- Diff visualization -------------

    def _show_inline_diff(self, old_str: str, new_str: str) -> None:
        self.txt_sel_old.delete('1.0', tk.END)
        self.txt_sel_new.delete('1.0', tk.END)
        sm = difflib.SequenceMatcher(a=old_str, b=new_str)

        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                self.txt_sel_old.insert(tk.END, old_str[i1:i2])
                self.txt_sel_new.insert(tk.END, new_str[j1:j2])
            elif op in ('delete', 'replace'):
                self.txt_sel_old.insert(tk.END, old_str[i1:i2], 'del')
            if op in ('insert', 'replace'):
                self.txt_sel_new.insert(tk.END, new_str[j1:j2], 'add')

    def _render_full_payloads(self, old_obj: Any, new_obj: Any) -> None:
        self.txt_old.delete('1.0', tk.END)
        self.txt_cur.delete('1.0', tk.END)
        self.txt_old.insert('1.0', pretty_json(old_obj))
        self.txt_cur.insert('1.0', pretty_json(new_obj))

    def _highlight_line_for_key_value(self, widget: tk.Text, leaf_key: str, value: Any) -> None:
        """
        Highlight the *entire line* containing `"leaf_key": value` (JSON-ish),
        falling back to key-only if the JSON representation is complex or absent.

        Also scrolls the widget so the highlighted line is visible. The synchronized
        scroll guard prevents this programmatic 'see' from immediately mirroring.

        NOTE: This pairs with the synchronized scrolling logic below. We first
        show/see the target line in each pane with the guard ON so they scroll
        independently to the right location, then resume sync for user scrolling.
        """
        tag = "linehit"
        widget.tag_remove(tag, "1.0", "end")
        widget.tag_configure(tag, background=UIConfig.COLOR_LINE_HIT_BG, foreground=UIConfig.COLOR_LINE_HIT_FG)
        
        text = widget.get("1.0", "end-1c")
        if not text.strip():
            return

        key_pat = re.escape(f'"{leaf_key}"') if leaf_key else None
        val_str = None
        try:
            if value is not None:
                val_str = json.dumps(value, ensure_ascii=False)
        except TypeError:
            # Non-JSON-serializable; fall back later
            val_str = None

        match = None
        if key_pat and val_str is not None:
            try:
                full_pat = re.compile(f"{key_pat}\\s*:\\s*{re.escape(val_str)}")
                match = full_pat.search(text)
            except re.error:
                match = None

        if not match and key_pat:
            # Key-only fallback
            try:
                key_only_pat = re.compile(key_pat)
                match = key_only_pat.search(text)
            except re.error:
                match = None

        if not match and val_str:
            # Value-only fallback (useful for arrays or numeric-only changes)
            try:
                val_only_pat = re.compile(re.escape(val_str))
                match = val_only_pat.search(text)
            except re.error:
                match = None

        if match:
            start_pos = f"1.0 + {match.start()} chars"
            line_start = widget.index(f"{start_pos} linestart")
            line_end = widget.index(f"{start_pos} lineend + 1 char")
            widget.tag_add(tag, line_start, line_end)
            widget.see(line_start)  # Make sure it's visible
        else:
            # Last resort: highlight the first line to give user a visual anchor.
            widget.tag_add(tag, "1.0", "2.0")
            widget.see("1.0")

    # ------------- Filtering / watch -------------

    def apply_watchlist(self):
        text = self.ent_watch.get().strip()
        self.watchlist = [w.strip().lower() for w in text.split(',') if w.strip()]
        # Retag rows without recomputing diffs
        for iid, meta in self._tree_meta.items():
            tags = list(self.tree.item(iid, 'tags'))
            if self._row_is_watched(meta.path) and 'watch' not in tags:
                tags.append('watch')
            elif not self._row_is_watched(meta.path) and 'watch' in tags:
                tags.remove('watch')
            self.tree.item(iid, tags=tuple(tags))
        self._filter_tree()

    def _row_is_watched(self, key_path: str) -> bool:
        if not self.watchlist: return False
        lk = key_path.lower()
        return any(w in lk for w in self.watchlist)

    def _filter_tree(self, *_):
        query = self.search_var.get().strip().lower()
        for iid, meta in self._tree_meta.items():
            is_visible = True
            if query:
                haystack = f"{meta.cfgkey} {meta.typ} {meta.path} {self._s(meta.old)} {self._s(meta.new)}".lower()
                is_visible = query in haystack
            if is_visible and self.only_watch.get():
                is_visible = self._row_is_watched(meta.path)
            
            # Detach/hide quickly; reinsert to original index when visible again
            if not is_visible:
                self.tree.detach(iid)
            elif iid not in self.tree.get_children(''):
                original_index = self._row_order.get(iid, 'end')
                self.tree.move(iid, '', original_index)

    # ------------- Exports (diffs) -------------

    def on_export_csv(self):
        if not self._tree_meta: return
        p = filedialog.asksaveasfilename(title='Save Visible Diffs as CSV',
                                         initialdir=self._get_initial_open_dir(),
                                         defaultextension='.csv',
                                         filetypes=[('CSV', '*.csv')])
        if not p: return
        
        try:
            with open(p, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Config Key', 'Type', 'Key Path', 'Old Value', 'New Value', 'Watched'])
                for iid in self.tree.get_children():
                    meta = self._tree_meta[iid]
                    writer.writerow([
                        meta.cfgkey, meta.typ, meta.path, 
                        self._s(meta.old), self._s(meta.new),
                        'YES' if self._row_is_watched(meta.path) else ''
                    ])
            messagebox.showinfo('Saved', f'CSV saved to:\n{p}')
        except IOError as e:
            messagebox.showerror('Error', f'Failed to save CSV:\n{e}')

    def on_export_txt(self):
        if not self._tree_meta: return
        p = filedialog.asksaveasfilename(title='Save Visible Diffs as TXT',
                                         initialdir=self._get_initial_open_dir(),
                                         defaultextension='.txt',
                                         filetypes=[('Text', '*.txt')])
        if not p: return

        grouped: Dict[str, List[RowMeta]] = {}
        for iid in self.tree.get_children():
            meta = self._tree_meta[iid]
            grouped.setdefault(meta.cfgkey, []).append(meta)

        lines = []
        for cfgkey, items in grouped.items():
            lines.append(f"=== Config Key: {cfgkey} ===")
            for typ in ('changed', 'added', 'removed'):
                diffs_of_type = [m for m in items if m.typ == typ]
                if not diffs_of_type: continue
                lines.append(f"\n-- {typ.UPPER()} ({len(diffs_of_type)}) --" if hasattr(str, 'UPPER') else f"\n-- {typ.upper()} ({len(diffs_of_type)}) --")
                for m in diffs_of_type:
                    lines.append(f"Key: {m.path}")
                    if m.typ == 'changed':
                        lines.append(f"  Old: {self._s(m.old)}")
                        lines.append(f"  New: {self._s(m.new)}")
                        lines.append("  Fragment (OLD):")
                        lines.append(self._format_fragment(m.path, m.old))
                        lines.append("  Fragment (NEW):")
                        lines.append(self._format_fragment(m.path, m.new))
                    elif m.typ == 'added':
                        lines.append(f"  New: {self._s(m.new)}")
                        lines.append("  Fragment (NEW):")
                        lines.append(self._format_fragment(m.path, m.new))
                    elif m.typ == 'removed':
                        lines.append(f"  Old: {self._s(m.old)}")
                        lines.append("  Fragment (OLD):")
                        lines.append(self._format_fragment(m.path, m.old))
            lines.append("\n" + "="*60 + "\n")

        try:
            with open(p, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            messagebox.showinfo('Saved', f'TXT saved to:\n{p}')
        except IOError as e:
            messagebox.showerror('Error', f'Failed to save TXT:\n{e}')
            
    def _format_fragment(self, path: str, value: Any) -> str:
        try:
            frag = build_fragment_from_path_value(path, value)
            pretty = pretty_json(frag)
            return '\n'.join(f"    {line}" for line in pretty.splitlines())
        except Exception:
            return "    (fragment generation error)"

    # ------------- Column confirm dialog -------------

    def _confirm_column_mapping(self, headers: List[str], mapping: Dict[str, int],
                                confidence: Dict[str, float]) -> Optional[Dict[str, int]]:
        dialog = tk.Toplevel(self)
        dialog.title("Confirm Column Mapping")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Please confirm or adjust the column mappings:",
                  font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, columnspan=3, pady=10, padx=10, sticky='w')

        combos: Dict[str, ttk.Combobox] = {}
        for i, role in enumerate(NEEDED_ROLES, 1):
            ttk.Label(dialog, text=f"{role}:").grid(row=i, column=0, padx=10, pady=5, sticky='e')
            combo = ttk.Combobox(dialog, values=headers, width=48, state="readonly")
            if role in mapping:
                combo.set(headers[mapping[role]])
            combo.grid(row=i, column=1, padx=5, pady=5, sticky='w')
            combos[role] = combo

            conf_val = confidence.get(role, 0.0)
            color = "green" if conf_val >= 0.7 else ("orange" if conf_val >= 0.4 else "red")
            ttk.Label(dialog, text=f"({conf_val:.0%})", foreground=color).grid(row=i, column=2, padx=5, pady=5, sticky='w')

        result = {"mapping": None}
        def on_ok():
            new_mapping = {role: headers.index(combo.get()) for role, combo in combos.items() if combo.get()}
            if len({idx for idx in new_mapping.values()}) != len(new_mapping):
                messagebox.showerror("Duplicate Columns", "Each role must be mapped to a unique column.", parent=dialog)
                return
            result["mapping"] = new_mapping
            dialog.destroy()
        
        btns = ttk.Frame(dialog)
        btns.grid(row=len(NEEDED_ROLES)+1, column=0, columnspan=3, pady=10)
        ttk.Button(btns, text="OK", command=on_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=6)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        self.wait_window(dialog)
        return result["mapping"]

    # ------------- Progress (threaded) -------------

    def _with_progress_threaded(self, task_fn, title: str, done_cb, determinate: bool = False):
        top = tk.Toplevel(self)
        top.title(title)
        top.transient(self)
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent closing

        ttk.Label(top, text=title, font=('TkDefaultFont', 10)).pack(padx=20, pady=(15, 6))
        pb = ttk.Progressbar(top, mode='determinate' if determinate else 'indeterminate', length=350, maximum=100)
        pb.pack(padx=20, pady=(0, 10))
        if not determinate: pb.start(10)

        status_lbl = ttk.Label(top, text="Starting...")
        status_lbl.pack(padx=20, pady=(0, 15))

        q_out, q_prog = queue.Queue(), queue.Queue()

        def worker():
            try:
                progress = lambda step, msg: q_prog.put((int(step), str(msg)))
                res = task_fn(progress if determinate else None)
                q_out.put(('ok', res))
            except Exception as e:
                q_out.put(('err', e))

        def poll():
            try:
                step, msg = q_prog.get_nowait()
                pb['value'] = max(0, min(100, step))
                status_lbl.config(text=msg)
            except queue.Empty:
                pass

            try:
                status, payload = q_out.get_nowait()
                if not determinate: pb.stop()
                top.destroy()
                if status == 'ok':
                    done_cb(payload)
                else:
                    messagebox.showerror("Error", f"An error occurred during loading:\n{payload}")
            except queue.Empty:
                self.after(100, poll)

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, poll)

    # ------------- Small helpers -------------

    def _reset_views(self):
        self.tree.delete(*self.tree.get_children())
        self._tree_meta.clear()
        self._row_order.clear()
        self.txt_sel_old.delete('1.0', tk.END)
        self.txt_sel_new.delete('1.0', tk.END)
        self.txt_old.delete('1.0', tk.END)
        self.txt_cur.delete('1.0', tk.END)
        self.v_changed.set('Changed: 0')
        self.v_added.set('Added: 0')
        self.v_removed.set('Removed: 0')
        self.search_var.set('')
        
        self.btn_clear.configure(state='disabled')
        self.btn_export_csv.configure(state='disabled')
        self.btn_export_txt.configure(state='disabled')

    def _s(self, v: Any) -> str:
        if v is None: return ''
        if isinstance(v, (dict, list)):
            try:
                s = json.dumps(v, ensure_ascii=False)
            except TypeError:
                s = str(v)
        else:
            s = str(v)
        return s if len(s) <= 2000 else s[:2000] + "â€¦"

    def _get_selected_diff_path(self) -> Optional[str]:
        """Returns the key path of the currently selected item in the tree."""
        if not self.tree.selection(): return None
        meta = self._tree_meta.get(self.tree.selection()[0])
        return meta.path if meta else None

    def _try_restore_selection(self, path_to_select: Optional[str]):
        """Finds and selects the item in the tree matching the given path."""
        if not path_to_select: return
        for iid, meta in self._tree_meta.items():
            if meta.path == path_to_select:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                break

    def show_shortcuts_help(self):
        messagebox.showinfo("Keyboard Shortcuts",
                            "Ctrl+O : Open file\n"
                            "Ctrl+S : Export visible rows to CSV\n"
                            "Ctrl+E : Export visible rows to TXT\n"
                            "Ctrl+F : Focus the filter box\n"
                            "Ctrl+M : Open Summary Dashboard\n\n"
                            "F5     : Run comparison on selected keys\n"
                            "Esc    : Remove focus from the current widget")

    # ------------- Scroll synchronization callbacks -------------

    def _on_yscroll(self, src_text: tk.Text, dst_text: tk.Text,
                    src_scrollbar: ttk.Scrollbar, dst_scrollbar: ttk.Scrollbar,
                    first: str, last: str) -> None:
        """
        Called by Text.yscrollcommand. Keeps BOTH scrollbars visually in sync and mirrors
        the fractional position to the other Text. Uses a guard to avoid infinite recursion.

        Scroll sync design:
          - As user scrolls either Text widget, Tk calls its yscrollcommand with (first,last).
          - We set the source scrollbar and mirror the fraction to the peer Text via yview_moveto(first).
          - We also set the peer scrollbar to keep its thumb in sync.
          - A small guard flag prevents recursive callbacks.
        """
        # Update this scrollbar regardless
        try:
            src_scrollbar.set(first, last)
        except Exception:
            pass

        if self._scroll_sync_active:
            return

        self._scroll_sync_active = True
        try:
            # Mirror scrollbar visuals
            try:
                dst_scrollbar.set(first, last)
            except Exception:
                pass
            # Mirror the fractional position of src -> dst
            try:
                dst_text.yview_moveto(first)
            except Exception:
                pass
        finally:
            self._scroll_sync_active = False

    def _on_scrollbar_y(self, src_text: tk.Text, dst_text: tk.Text,
                        src_scrollbar: ttk.Scrollbar, dst_scrollbar: ttk.Scrollbar,
                        *args) -> None:
        """
        Called by Scrollbar.command. Scroll BOTH Text widgets with the same args.
        Also keeps both scrollbars visually consistent. Guard prevents recursion.
        """
        self._scroll_sync_active = True
        try:
            # Apply to both text widgets
            try:
                src_text.yview(*args)
            except Exception:
                pass
            try:
                dst_text.yview(*args)
            except Exception:
                pass

            # Read back the fractions from the source and set both scrollbars
            try:
                first, last = src_text.yview()
                src_scrollbar.set(first, last)
                dst_scrollbar.set(first, last)
            except Exception:
                pass
        finally:
            self._scroll_sync_active = False

    # ------------- SUMMARY DASHBOARD -------------

    def on_view_summary(self):
        """Open the Summary Dashboard: pivot table + chart with readable labels + search + Top-N."""
        if not self.rows:
            messagebox.showinfo("Summary", "Load a file first (File â†’ Open).")
            return

        win = tk.Toplevel(self)
        win.title("Summary â€“ Rows per Config Name")
        win.geometry("980x680")
        win.minsize(760, 480)

        # State on the window instance
        win.pivot_data: List[Tuple[str, int]] = []  # [(Config Name, Count), ...]
        win.sort_mode = tk.StringVar(value='count_desc')  # 'count_desc' or 'name'
        win.topn_var = tk.IntVar(value=30)  # 0 = show all
        win.search_var = tk.StringVar(value="")
        win.show_values = tk.BooleanVar(value=True)

        win.figure = None
        win.canvas = None

        # ------------- Controls (top bar) -------------
        ctrl = ttk.Frame(win)
        ctrl.pack(fill=tk.X, padx=10, pady=8)

        # Search
        ttk.Label(ctrl, text="Search:").pack(side=tk.LEFT)
        ent_search = ttk.Entry(ctrl, textvariable=win.search_var, width=32)
        ent_search.pack(side=tk.LEFT, padx=(4, 10))

        # Sort options
        ttk.Label(ctrl, text="Sort by:").pack(side=tk.LEFT)
        ttk.Radiobutton(ctrl, text="Count (desc)", value='count_desc', variable=win.sort_mode,
                        command=lambda: update_view()).pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(ctrl, text="Config Name", value='name', variable=win.sort_mode,
                        command=lambda: update_view()).pack(side=tk.LEFT, padx=6)

        # Top-N
        ttk.Label(ctrl, text="Top-N:").pack(side=tk.LEFT, padx=(14, 2))
        spn_topn = ttk.Spinbox(ctrl, from_=0, to=1000, width=6, textvariable=win.topn_var,
                               command=lambda: update_view())
        spn_topn.pack(side=tk.LEFT)
        ttk.Label(ctrl, text="(0 = All)").pack(side=tk.LEFT, padx=(4, 12))

        # Values on bars
        ttk.Checkbutton(ctrl, text="Show values on bars", variable=win.show_values,
                        command=lambda: update_view()).pack(side=tk.LEFT, padx=(6, 0))

        # Export buttons
        ttk.Button(ctrl, text="Export Summary CSV", command=lambda: export_summary_csv()).pack(side=tk.RIGHT, padx=6)
        if HAS_MPL:
            ttk.Button(ctrl, text="Save Chart PNG", command=lambda: save_chart_png()).pack(side=tk.RIGHT, padx=6)

        # ------------- Body: pivot table + chart -------------
        body = ttk.PanedWindow(win, orient=tk.VERTICAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Pivot table
        tbl_frame = ttk.Frame(body)
        body.add(tbl_frame, weight=2)

        columns = ('Config Name', 'Count')
        tree = ttk.Treeview(tbl_frame, columns=columns, show='headings', selectmode='browse')
        tree.heading('Config Name', text='Config Name', command=lambda: set_sort('name'))
        tree.heading('Count', text='Count', command=lambda: set_sort('count_desc'))
        tree.column('Config Name', width=620, anchor='w')
        tree.column('Count', width=120, anchor='e')
        vs = ttk.Scrollbar(tbl_frame, orient='vertical', command=tree.yview)
        hs = ttk.Scrollbar(tbl_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscroll=vs.set, xscroll=hs.set)
        tree.grid(row=0, column=0, sticky='nsew')
        vs.grid(row=0, column=1, sticky='ns')
        hs.grid(row=1, column=0, sticky='ew')
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        # Double-click: jump to Config Name in main app
        def on_row_open(_evt=None):
            sel = tree.selection()
            if not sel:
                return
            cfg_name = tree.item(sel[0], 'values')[0]
            try:
                self.cmb_name.set(cfg_name)
                self.on_name_selected()
                self.focus_set()
            except Exception:
                pass
        tree.bind('<Double-1>', on_row_open)

        # Chart area
        chart_frame = ttk.Frame(body)
        body.add(chart_frame, weight=3)

        if not HAS_MPL:
            ttk.Label(chart_frame, text="Chart unavailable. Install matplotlib for visualization.").pack(pady=10)

        status = ttk.Label(chart_frame, text="Generating summaryâ€¦")
        status.pack(anchor='w', padx=6, pady=(6, 0))

        # --- helpers inside Summary scope ---

        def set_sort(mode: str):
            if mode not in ('count_desc', 'name'):
                return
            win.sort_mode.set(mode)
            update_view()

        def compute_pivot() -> List[Tuple[str, int]]:
            """Return [(name, count)] using pandas if available else dict."""
            if pd is not None:
                try:
                    df = pd.DataFrame(self.rows)
                    if 'Config Name' not in df.columns:
                        return []
                    ser = df['Config Name'].fillna('').astype(str).str.strip()
                    ser = ser[ser != '']
                    vc = ser.value_counts()
                    return [(idx, int(cnt)) for idx, cnt in vc.items()]
                except Exception:
                    pass

            counts: Dict[str, int] = {}
            for r in self.rows:
                nm = (r.get('Config Name') or '').strip()
                if nm:
                    counts[nm] = counts.get(nm, 0) + 1
            return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))

        def populate_table(data: List[Tuple[str, int]]):
            tree.delete(*tree.get_children())
            for name, cnt in data:
                tree.insert('', tk.END, values=(name, cnt))

        def shorten(label: str, maxlen: int = 26) -> str:
            return label if len(label) <= maxlen else (label[:maxlen - 1] + "â€¦")

        def apply_filters(data: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
            # Sort first
            mode = win.sort_mode.get()
            if mode == 'name':
                data = sorted(data, key=lambda kv: kv[0].lower())
            else:
                data = sorted(data, key=lambda kv: (-kv[1], kv[0].lower()))
            # Search filter
            q = win.search_var.get().strip().lower()
            if q:
                data = [d for d in data if q in d[0].lower()]
            # Top-N
            n = max(0, int(win.topn_var.get() or 0))
            if n > 0:
                data = data[:n]
            return data

        def draw_chart(data: List[Tuple[str, int]]):
            if not HAS_MPL:
                return

            # Clear old canvas if any
            for w in chart_frame.pack_slaves():
                if isinstance(w, ttk.Label) and w is not status:
                    w.destroy()
            if win.canvas:
                try:
                    win.canvas.get_tk_widget().destroy()
                except Exception:
                    pass
                win.canvas = None
                win.figure = None

            if not data:
                ttk.Label(chart_frame, text="No data to chart (check filters).").pack(pady=10)
                return

            names = [n for n, _ in data]
            counts = [c for _, c in data]
            ncat = len(names)

            # Dynamic figure height: enough space for labels; clamp to sane bounds.
            height = max(3.2, min(16.0, 0.35 * ncat + 2.2))
            fig = Figure(figsize=(10, height), dpi=100)
            ax = fig.add_subplot(111)

            # Horizontal bar chart for readability with many categories
            ax.barh(range(ncat), counts)

            # Tick labels
            labels = [shorten(n, 38) for n in names]
            ax.set_yticks(list(range(ncat)))
            # Font size scales down slightly as categories grow
            fs = 10 if ncat <= 15 else 9 if ncat <= 30 else 8 if ncat <= 50 else 7
            ax.set_yticklabels(labels, fontsize=fs)

            ax.set_xlabel("Count")
            ax.set_ylabel("Config Name")
            ax.invert_yaxis()  # Largest at the top
            ax.set_title("Rows per Config Name")
            ax.margins(x=0.05)

            # Show values at bar ends (optional)
            if win.show_values.get():
                xmax = max(counts) if counts else 0
                offset = 0.01 * (xmax or 1)
                for i, v in enumerate(counts):
                    ax.text(v + offset, i, str(v), va='center', fontsize=fs)

            # Wider left margin for long labels
            max_label = max((len(s) for s in labels), default=0)
            left = 0.22 if max_label < 20 else 0.32 if max_label < 32 else 0.42
            fig.subplots_adjust(left=left)
            fig.tight_layout()

            win.figure = fig
            win.canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            win.canvas.draw()
            win.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=6)

        def export_summary_csv():
            if not win.pivot_data:
                messagebox.showinfo("Export", "No summary data.")
                return
            p = filedialog.asksaveasfilename(
                title='Save Summary as CSV',
                initialdir=self._get_initial_open_dir(),
                defaultextension='.csv',
                filetypes=[('CSV', '*.csv')]
            )
            if not p:
                return
            try:
                with open(p, 'w', encoding='utf-8', newline='') as f:
                    w = csv.writer(f)
                    w.writerow(['Config Name', 'Count'])
                    # Export the *currently* filtered/sorted view
                    for name, cnt in apply_filters(list(win.pivot_data)):
                        w.writerow([name, cnt])
                messagebox.showinfo("Export", f"Summary saved to:\n{p}")
            except Exception as e:
                messagebox.showerror("Export", f"Failed to write CSV:\n{e}")

        def save_chart_png():
            if not HAS_MPL or not win.figure:
                messagebox.showinfo("Chart", "Chart unavailable.")
                return
            p = filedialog.asksaveasfilename(
                title='Save Chart as PNG',
                initialdir=self._get_initial_open_dir(),
                defaultextension='.png',
                filetypes=[('PNG', '*.png')]
            )
            if not p:
                return
            try:
                win.figure.savefig(p, dpi=150, bbox_inches='tight')
                messagebox.showinfo("Chart", f"Chart saved to:\n{p}")
            except Exception as e:
                messagebox.showerror("Chart", f"Failed to save chart:\n{e}")

        def update_view(*_):
            """Rebuild table and chart from filters."""
            data = apply_filters(list(win.pivot_data))
            populate_table(data)
            draw_chart(data)
            status.configure(text=f"Summary ready. {len(win.pivot_data)} group(s). Showing {len(data)}.")

        # live updates on search
        win.search_var.trace_add('write', lambda *_: update_view())

        # Background compute to keep UI responsive
        def worker():
            data = compute_pivot()
            self.after(0, lambda: after_pivot_ready(data))

        def after_pivot_ready(data: List[Tuple[str, int]]):
            win.pivot_data = data
            update_view()

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- END SUMMARY DASHBOARD ----------------

# -------------------
# Main entrypoint
# -------------------

if __name__ == '__main__':
    app = PayloadDiffViewerApp()
    app.mainloop()
