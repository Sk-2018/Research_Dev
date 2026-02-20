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
"""

from __future__ import annotations

import os
import re
import csv
import ast
import sys
import json
import time
import math
import queue
import threading
import difflib
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional, Iterable

# UI
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

# Data libs (pandas optional but recommended)
try:
    import pandas as pd
except Exception:
    pd = None

# DeepDiff
from deepdiff import DeepDiff

# Optional pretty JSON library
try:
    import orjson
except Exception:
    orjson = None


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

    # Highlight colors
    COLOR_CHANGED = '#FFF5CC'  # amber (row background)
    COLOR_ADDED   = '#E6FFED'  # light green
    COLOR_REMOVED = '#FFECEC'  # light red

    # Strong line highlight (works on Windows light/dark)
    COLOR_LINE_HIT_BG = '#ffeb3b'
    COLOR_LINE_HIT_FG = 'black'


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
        txt = tk.Text(top, wrap='word')
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert('1.0', self.summary_text())


# --------------------------
# Helpers: JSON + Deep paths
# --------------------------

TRAILING_COMMAS = re.compile(r',\s*([}\]])')

def parse_jsonish_verbose(s: str) -> Tuple[Any, str]:
    """
    Return (parsed_obj, error_message_if_any).
    Tries strict JSON → trailing-comma fix → ast.literal_eval
    """
    t = (s or '').strip()
    if not t:
        return {}, "Empty payload"

    # Strict JSON
    try:
        return json.loads(t), ""
    except Exception:
        pass

    # Remove trailing commas
    try:
        t2 = TRAILING_COMMAS.sub(r'\1', t)
        return json.loads(t2), ""
    except Exception:
        pass

    # Python literal
    try:
        return ast.literal_eval(t), ""
    except Exception as e3:
        return {}, f"Failed to parse payload ({e3.__class__.__name__})"


def pretty_json(obj: Any) -> str:
    if obj is None:
        return ""
    try:
        if orjson is not None:
            return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode()
    except Exception:
        pass
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def dd_path_to_key(p: str) -> str:
    """
    DeepDiff path "root['a'][2]['b']" → "a[2].b"
    """
    if not p:
        return ""
    p = p.replace("root", "")
    p = re.sub(r"\['([^']+)'\]", r".\1", p)
    p = re.sub(r'^\.', '', p)
    return p


def _path_tokens(path: str) -> List[str]:
    """
    Turn "a[2].b.c[10]" into tokens: ['a', '[2]', 'b', 'c', '[10]']
    """
    if not path:
        return []
    toks = []
    i = 0
    buf = []
    while i < len(path):
        ch = path[i]
        if ch == '[':
            # flush buffer as name
            if buf:
                toks.append(''.join(buf))
                buf = []
            j = i
            while j < len(path) and path[j] != ']':
                j += 1
            if j < len(path):
                toks.append(path[i:j+1])
                i = j + 1
                continue
        elif ch == '.':
            if buf:
                toks.append(''.join(buf))
                buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if buf:
        toks.append(''.join(buf))
    return toks


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
    except Exception:
        return None


def build_fragment_from_path_value(path: str, value: Any) -> Any:
    """
    Make a minimal JSON fragment showing the leaf at `path` with `value`.
    Example: path="a.b[2].c"  => {"a":{"b":[null,null,{"c": value}]}}
    """
    tokens = _path_tokens(path)
    if not tokens:
        return value

    def ensure_list_len(L: list, n: int) -> None:
        while len(L) <= n:
            L.append(None)

    root: Any = {}
    cur: Any = root
    parent: Any = None
    last_token = tokens[-1]
    path_so_far: List[str] = []

    for i, tok in enumerate(tokens):
        is_last = (i == len(tokens) - 1)
        if tok.startswith('[') and tok.endswith(']'):
            # list index
            idx = int(tok[1:-1])
            # ensure parent is list
            if not isinstance(cur, list):
                # transform cur into list at this level
                newlist: List[Any] = []
                # place newlist under parent (if any)
                if parent is None:
                    # root should be list in this weird case
                    root = newlist
                else:
                    # find last non-index token to assign
                    prev = tokens[i-1] if i > 0 else None
                    if prev and not (prev.startswith('[') and prev.endswith(']')):
                        parent[prev] = newlist
                cur = newlist
            ensure_list_len(cur, idx)
            if is_last:
                cur[idx] = value
                return root
            # prepare placeholder if None
            if cur[idx] is None:
                # next token decides dict or list
                nxt = tokens[i+1]
                if nxt.startswith('['):
                    cur[idx] = []
                else:
                    cur[idx] = {}
            parent = cur
            cur = cur[idx]
        else:
            # dict key
            if not isinstance(cur, dict):
                # make dict at this level
                newdict: Dict[str, Any] = {}
                if parent is None:
                    root = newdict
                else:
                    # parent must be a list; place dict in it
                    if isinstance(parent, list):
                        # cannot know index, so skip; we'll just replace
                        pass
                cur = newdict
            if is_last:
                cur[tok] = value
                return root
            if tok not in cur or cur[tok] is None:
                # next decides structure
                nxt = tokens[i+1]
                cur[tok] = [] if nxt.startswith('[') else {}
            parent = cur
            cur = cur[tok]

    # fallback
    return root if root else value


# ---------------------------------
# File reading helpers (CSV/Excel)
# ---------------------------------

def _bump_csv_field_limit():
    try:
        csv.field_size_limit(sys.maxsize)
    except Exception:
        try:
            csv.field_size_limit(10**9)
        except Exception:
            pass


def _sniff_csv_delimiter(path: str) -> str:
    default = ','
    ext = os.path.splitext(path)[1].lower()
    if ext == '.tsv':
        return '\t'
    try:
        with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            sample = f.read(8192)
            f.seek(0)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
    except Exception:
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
        # Fallback to simple loader
        return _load_csv_like_headers_rows(path)

    delim = _sniff_csv_delimiter(path)

    # crude estimate for progress
    try:
        file_size = os.path.getsize(path)
    except Exception:
        file_size = None

    headers = None
    all_rows: List[List[str]] = []
    total_bytes = 0

    with open(path, 'rb') as fb:
        # consume header line bytes for better estimation
        head = fb.readline()
        hdr_bytes = len(head)

    # read chunks with pandas
    chunks = pd.read_csv(path, dtype=str, chunksize=chunk_size,
                         sep=delim, engine='python', on_bad_lines='skip')
    for i, chunk in enumerate(chunks, 1):
        if headers is None:
            headers = [str(c) for c in chunk.columns]
        chunk = chunk.astype(str).fillna("")
        rows = chunk.values.tolist()
        all_rows.extend(rows)

        if progress_cb and file_size:
            # Approx based on per chunk rows * average line length guess
            approx_bytes = i * chunk_size * 40  # heuristic
            step = min(100, int((approx_bytes / max(1, file_size)) * 100))
            progress_cb(step, f"Read ~{i*chunk_size:,} rows")

    return headers or [], all_rows


def _excel_headers_rows(path: str, sheet: Optional[str] = None) -> Tuple[List[str], List[List[str]]]:
    if pd is None:
        raise RuntimeError("pandas is required to read Excel files")

    if sheet:
        df = pd.read_excel(path, sheet_name=sheet, dtype=str)
        df = df.astype(str).fillna("")
        return [str(c) for c in df.columns], df.values.tolist()

    # Load all sheets, pick best by header similarity
    book = pd.read_excel(path, sheet_name=None, dtype=str)
    best_headers: List[str] = []
    best_rows: List[List[str]] = []
    best_score = -1.0

    for sh_name, df in book.items():
        tmp = df.astype(str).fillna("")
        headers = [str(c) for c in tmp.columns]
        score = _score_headers(headers)
        if score > best_score:
            best_score = score
            best_headers = headers
            best_rows = tmp.values.tolist()

    return best_headers, best_rows


# --------------------------
# Column detection / mapping
# --------------------------

ROLE_SYNONYMS = {
    "Config Name": ["config name", "configname", "config_name", "cfg name", "cfgname", "cfg_name"],
    "Config Key":  ["config key", "cfg key", "config_key", "cfg_key", "key", "identifier", "id"],
    "CURRENT PAYLOAD": ["current payload", "current json", "new payload", "payload", "current", "new json"],
    "OLD PAYLOAD":     ["old payload", "old json", "previous payload", "previous json", "old"]
}

NEEDED_ROLES = ["Config Name", "Config Key", "CURRENT PAYLOAD", "OLD PAYLOAD"]

def _header_confidence(header: str, role: str) -> float:
    h = header.strip().lower()
    syns = ROLE_SYNONYMS.get(role, [])
    # direct match weight
    direct = 0.0
    for s in syns:
        if s in h:
            direct = max(direct, 1.0 if h == s else 0.7)
    # weak hints
    hints = 0.0
    if role == "Config Key":
        if "key" in h or "id" in h:
            hints = max(hints, 0.5)
    if role == "Config Name":
        if "name" in h:
            hints = max(hints, 0.5)
    if role.endswith("PAYLOAD"):
        if "payload" in h or "json" in h:
            hints = max(hints, 0.6)
        if "current" in h and "CURRENT" in role:
            hints = max(hints, 0.9)
        if "old" in h and "OLD" in role:
            hints = max(hints, 0.9)
        if "new" in h and "CURRENT" in role:
            hints = max(hints, 0.8)

    return max(direct, hints)


def _score_headers(headers: List[str]) -> float:
    # simple: how many needed role-like headers present
    score = 0.0
    for r in NEEDED_ROLES:
        best = 0.0
        for h in headers:
            best = max(best, _header_confidence(h, r))
        score += best
    return score


def detect_best_columns(headers: List[str], raw_rows: List[List[str]]) -> Tuple[Dict[str, int], Dict[str, float]]:
    """
    Return (mapping, confidence_per_role)
      mapping: {role: column_index}
    """
    conf: Dict[str, float] = {}
    mapping: Dict[str, int] = {}
    for role in NEEDED_ROLES:
        best_i = None
        best_c = -1.0
        for i, h in enumerate(headers):
            c = _header_confidence(h, role)
            if c > best_c:
                best_c = c
                best_i = i
        if best_i is not None and best_c > 0:
            mapping[role] = best_i
            conf[role] = best_c
    return mapping, conf


def assemble_rows(headers: List[str], raw_rows: List[List[str]], mapping: Dict[str, int]) -> List[Dict[str, str]]:
    col_index = {role: mapping.get(role, -1) for role in NEEDED_ROLES}
    rows: List[Dict[str, str]] = []
    for raw in raw_rows:
        row = {
            "Config Name": raw[col_index["Config Name"]] if col_index["Config Name"] >= 0 and col_index["Config Name"] < len(raw) else "",
            "Config Key":  raw[col_index["Config Key"]] if col_index["Config Key"] >= 0 and col_index["Config Key"] < len(raw) else "",
            "CURRENT PAYLOAD": raw[col_index["CURRENT PAYLOAD"]] if col_index["CURRENT PAYLOAD"] >= 0 and col_index["CURRENT PAYLOAD"] < len(raw) else "",
            "OLD PAYLOAD":     raw[col_index["OLD PAYLOAD"]] if col_index["OLD PAYLOAD"] >= 0 and col_index["OLD PAYLOAD"] < len(raw) else "",
            # Optional timestamps/flags if present
            "config_eff_ts": "",
            "rec_sts": "",
            "param_exp_ts": ""
        }
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
        self.title("Payload Diff Viewer (Config Name → Current vs Old)")
        self.geometry(f"{UIConfig.WINDOW_W}x{UIConfig.WINDOW_H}")
        self.minsize(UIConfig.MIN_W, UIConfig.MIN_H)

        # state
        self.rows: List[Dict[str, str]] = []
        self.by_name: Dict[str, List[Dict[str, str]]] = {}
        self.parse_logger = ParseLogger()

        # watch & filter
        self.watchlist: List[str] = []
        self.only_watch = tk.BooleanVar(value=False)
        self.arrays_as_sets = tk.BooleanVar(value=False)

        # ui bits
        self._tree_meta: Dict[str, RowMeta] = {}
        self.search_var = tk.StringVar()

        # build
        self._build_ui()
        self._bind_shortcuts()

    # ------------- UI --------------

    def _build_ui(self):
        # menu
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open… (Ctrl+O)", command=self.on_open)
        filemenu.add_separator()
        filemenu.add_command(label="Export CSV (Ctrl+S)", command=self.on_export_csv)
        filemenu.add_command(label="Export TXT (Ctrl+E)", command=self.on_export_txt)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Show Parse Log", command=lambda: self.parse_logger.show(self))
        helpmenu.add_separator()
        helpmenu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts_help)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.config(menu=menubar)

        # top controls
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(top, text='Open…', command=self.on_open).pack(side=tk.LEFT)

        ttk.Label(top, text='Config Name:').pack(side=tk.LEFT, padx=(12, 4))
        self.cmb_name = ttk.Combobox(top, state='disabled', width=36)
        self.cmb_name.pack(side=tk.LEFT)
        self.cmb_name.bind('<<ComboboxSelected>>', self.on_name)

        ttk.Label(top, text='Config Keys:').pack(side=tk.LEFT, padx=(12, 4))
        self.lst_keys = tk.Listbox(top, selectmode=tk.EXTENDED, width=38, height=6, exportselection=False)
        self.lst_keys.pack(side=tk.LEFT)
        self.lst_keys.configure(state=tk.DISABLED)

        self.btn_compare = ttk.Button(top, text='Compare (F5)', state='disabled', command=self.on_compare)
        self.btn_compare.pack(side=tk.LEFT, padx=(12, 0))

        self.btn_export_csv = ttk.Button(top, text='Export CSV', state='disabled', command=self.on_export_csv)
        self.btn_export_csv.pack(side=tk.LEFT, padx=(6, 0))
        self.btn_export_txt = ttk.Button(top, text='Export TXT', state='disabled', command=self.on_export_txt)
        self.btn_export_txt.pack(side=tk.LEFT, padx=(6, 0))

        # status label
        self.lbl = ttk.Label(self, text='Open a CSV/Excel file to begin.')
        self.lbl.pack(anchor='w', padx=12)

        # options row (arrays mode, watchlist)
        opt = ttk.Frame(self)
        opt.pack(fill=tk.X, padx=10, pady=(2, 6))

        ttk.Label(opt, text='Arrays:').pack(side=tk.LEFT)
        ttk.Radiobutton(opt, text='by index', variable=self.arrays_as_sets, value=False).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Radiobutton(opt, text='as set (ignore order)', variable=self.arrays_as_sets, value=True).pack(side=tk.LEFT)

        ttk.Label(opt, text='  Watch keys:').pack(side=tk.LEFT, padx=(14, 4))
        self.ent_watch = ttk.Entry(opt, width=64)
        self.ent_watch.pack(side=tk.LEFT)
        self.ent_watch.insert(0, 'numericCurrencyCode, schemeConfigs, processingAgreements')
        ttk.Checkbutton(opt, text='Only watch', variable=self.only_watch, command=self._filter_tree).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(opt, text='Apply', command=self.apply_watchlist).pack(side=tk.LEFT, padx=(8, 0))

        # filter row + counts
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

        # watch tag
        default_font = tkfont.nametofont("TkDefaultFont")
        bold_font = tkfont.Font(**default_font.configure())
        bold_font.configure(weight='bold')
        self.tree.tag_configure('watch', foreground='#0b5bb5', font=bold_font)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # Lower panes: inline diff | full JSONs
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # inline diff panel
        fmid = ttk.Frame(paned)
        paned.add(fmid, weight=1)

        ttk.Label(fmid, text='Selected field – inline character diff (Old vs Current)').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,4))

        left = ttk.Frame(fmid)
        left.grid(row=1, column=0, sticky='nsew', padx=(0, 6))
        right = ttk.Frame(fmid)
        right.grid(row=1, column=1, sticky='nsew', padx=(6, 0))
        fmid.columnconfigure(0, weight=1)
        fmid.columnconfigure(1, weight=1)
        fmid.rowconfigure(1, weight=1)

        ttk.Label(left, text='OLD (selected key)').pack(anchor='w')
        self.txt_sel_old = tk.Text(left, wrap='word', height=UIConfig.INLINE_ROWS)
        self.txt_sel_old.pack(fill=tk.BOTH, expand=True)
        self.txt_sel_old.tag_configure('del', background='#ffcccc')

        ttk.Label(right, text='CURRENT (selected key)').pack(anchor='w')
        self.txt_sel_new = tk.Text(right, wrap='word', height=UIConfig.INLINE_ROWS)
        self.txt_sel_new.pack(fill=tk.BOTH, expand=True)
        self.txt_sel_new.tag_configure('add', background='#c2f0c2')

        # full JSONs
        fbot = ttk.Frame(paned)
        paned.add(fbot, weight=2)

        jl = ttk.Frame(fbot)
        jl.grid(row=0, column=0, sticky='nsew')
        jr = ttk.Frame(fbot)
        jr.grid(row=0, column=1, sticky='nsew')
        fbot.columnconfigure(0, weight=1)
        fbot.columnconfigure(1, weight=1)
        fbot.rowconfigure(0, weight=1)

        ttk.Label(jl, text='OLD Payload (pretty JSON)').pack(anchor='w')
        self.txt_old = tk.Text(jl, wrap='none')
        sc1y = ttk.Scrollbar(jl, orient='vertical', command=self.txt_old.yview)
        sc1x = ttk.Scrollbar(jl, orient='horizontal', command=self.txt_old.xview)
        self.txt_old.configure(yscrollcommand=sc1y.set, xscrollcommand=sc1x.set)
        self.txt_old.pack(fill=tk.BOTH, expand=True)
        sc1y.pack(side=tk.RIGHT, fill=tk.Y)
        sc1x.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(jr, text='CURRENT Payload (pretty JSON)').pack(anchor='w')
        self.txt_cur = tk.Text(jr, wrap='none')
        sc2y = ttk.Scrollbar(jr, orient='vertical', command=self.txt_cur.yview)
        sc2x = ttk.Scrollbar(jr, orient='horizontal', command=self.txt_cur.xview)
        self.txt_cur.configure(yscrollcommand=sc2y.set, xscrollcommand=sc2x.set)
        self.txt_cur.pack(fill=tk.BOTH, expand=True)
        sc2y.pack(side=tk.RIGHT, fill=tk.Y)
        sc2x.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_shortcuts(self):
        self.bind('<Control-o>', lambda e: self.on_open())
        self.bind('<Control-s>', lambda e: self.on_export_csv())
        self.bind('<Control-e>', lambda e: self.on_export_txt())
        self.bind('<Control-f>', lambda e: (self.filter_entry.focus_set(), self.filter_entry.select_range(0, tk.END)))
        self.bind('<F5>', lambda e: self.on_compare())
        self.bind('<Escape>', lambda e: self.focus_set())

    # ------------- Actions -------------

    def _validate_file(self, path: str) -> Tuple[bool, str]:
        if not os.path.exists(path):
            return False, "File not found."
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.csv', '.tsv', '.txt', '.xlsx', '.xls'):
            return False, f"Unsupported file type: {ext}"
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > 1024:
            return False, f"File is too large ({size_mb:.1f} MB)."
        return True, ""

    def on_open(self):
        p = filedialog.askopenfilename(
            title="Select CSV/TSV/TXT/XLSX/XLS",
            filetypes=[
                ("All supported", "*.csv *.tsv *.txt *.xlsx *.xls"),
                ("Excel", "*.xlsx *.xls"),
                ("CSV/TSV/TXT", "*.csv *.tsv *.txt"),
                ("All files", "*.*"),
            ]
        )
        if not p:
            return
        ok, why = self._validate_file(p)
        if not ok:
            messagebox.showerror("File error", why)
            return

        ext = os.path.splitext(p)[1].lower()
        size_mb = os.path.getsize(p) / (1024 * 1024)
        use_chunked = (pd is not None) and (ext in ('.csv', '.tsv', '.txt')) and (size_mb > 50)

        def load_task(progress_cb=None):
            if ext in ('.csv', '.tsv', '.txt'):
                if use_chunked:
                    return _load_csv_like_headers_rows_chunked(p, chunk_size=20000, progress_cb=progress_cb)
                return _load_csv_like_headers_rows(p)
            if ext in ('.xlsx', '.xls'):
                return _excel_headers_rows(p, sheet=None)
            # fallback using pandas
            if pd is None:
                raise ValueError("pandas is required for this file format")
            df = pd.read_csv(p, dtype=str, engine="python")
            df = df.astype(str).fillna("")
            return [str(c) for c in df.columns], df.values.tolist()

        def on_loaded(result):
            headers, raw_rows = result
            if not headers:
                messagebox.showwarning('No data', 'File appears empty.')
                return

            mapping, conf = detect_best_columns(headers, raw_rows)
            missing = [r for r in NEEDED_ROLES if r not in mapping]
            low_conf = [r for r in NEEDED_ROLES if conf.get(r, 0) < 0.70]

            if missing or low_conf:
                mapping2 = self._confirm_column_mapping(headers, mapping, conf)
                if not mapping2:
                    messagebox.showinfo("Cancelled", "Column mapping not confirmed.")
                    return
                mapping = mapping2

            rows = assemble_rows(headers, raw_rows, mapping)
            self._finalize_load(rows)

        self._with_progress_threaded(
            load_task,
            title=("Loading large file..." if use_chunked else "Loading file..."),
            done_cb=on_loaded,
            determinate=use_chunked
        )

    def _finalize_load(self, rows: List[Dict[str, str]]):
        self.rows = rows
        self.by_name.clear()

        for r in rows:
            nm = (r.get('Config Name') or '').strip()
            if nm:
                self.by_name.setdefault(nm, []).append(r)

        names = sorted(self.by_name.keys())
        self.cmb_name.configure(state='readonly', values=names)
        self.cmb_name.set('')
        self.lst_keys.configure(state=tk.DISABLED)
        self.lst_keys.delete(0, tk.END)

        self.btn_compare.configure(state='disabled')
        self.btn_export_csv.configure(state='disabled')
        self.btn_export_txt.configure(state='disabled')

        base = f"Loaded {len(rows)} rows. Select Config Name and Config Keys, then Compare."
        if self.parse_logger.entries:
            base += f" | Parse log entries: {len(self.parse_logger.entries)} (Help → Parse Log)"
        self.lbl.configure(text=base)
        self._reset_views()

    def on_name(self, _evt=None):
        n = self.cmb_name.get().strip()
        self._reset_views()
        self.btn_export_csv.configure(state='disabled')
        self.btn_export_txt.configure(state='disabled')
        self.btn_compare.configure(state='disabled')

        self.lst_keys.configure(state=tk.DISABLED)
        self.lst_keys.delete(0, tk.END)
        if not n:
            return

        keys = sorted({(r.get('Config Key') or '').strip()
                       for r in self.by_name.get(n, [])
                       if r.get('Config Key')})
        for k in keys:
            self.lst_keys.insert(tk.END, k)
        self.lst_keys.configure(state=tk.NORMAL)
        if keys:
            self.btn_compare.configure(state='normal')

    def on_compare(self):
        n = self.cmb_name.get().strip()
        if not n:
            messagebox.showwarning('Pick a Config Name', 'Select a Config Name first.')
            return

        sel_indices = self.lst_keys.curselection()
        if not sel_indices:
            messagebox.showwarning('Pick Config Keys', 'Select one or more Config Keys to compare.')
            return

        selected_keys = [self.lst_keys.get(i) for i in sel_indices]
        rows = [r for r in self.by_name.get(n, []) if (r.get('Config Key') or '').strip() in selected_keys]

        # For each key, pick latest by config_eff_ts if available
        keyed: Dict[str, Dict[str, str]] = {}
        for r in rows:
            k = (r.get('Config Key') or '').strip()
            prev = keyed.get(k)
            if prev is None:
                keyed[k] = r
            else:
                if (r.get('config_eff_ts') or '') > (prev.get('config_eff_ts') or ''):
                    keyed[k] = r

        # Compute diffs
        diffs: List[Tuple[str, str, str, Any, Any, Any, Any]] = []  # (cfgkey, typ, path, old, new, old_obj, new_obj)
        changed = added = removed = 0

        ignore_order = bool(self.arrays_as_sets.get())

        for k, row in keyed.items():
            cur_raw = row.get('CURRENT PAYLOAD', '')
            old_raw = row.get('OLD PAYLOAD', '')

            cur_obj, err1 = parse_jsonish_verbose(cur_raw)
            old_obj, err2 = parse_jsonish_verbose(old_raw)
            if err1:
                self.parse_logger.log(f"[{n} / {k}] CURRENT parse: {err1}", context=cur_raw[:200])
            if err2:
                self.parse_logger.log(f"[{n} / {k}] OLD parse: {err2}", context=old_raw[:200])

            dd = DeepDiff(old_obj, cur_obj, ignore_order=ignore_order, verbose_level=2)

            # values_changed
            for path, change in dd.get('values_changed', {}).items():
                dotted = dd_path_to_key(path)
                o = change.get('old_value')
                v = change.get('new_value')
                diffs.append((k, 'changed', dotted, o, v, old_obj, cur_obj))
                changed += 1

            # dictionary_item_added → usually set of paths
            dia = dd.get('dictionary_item_added', set())
            if isinstance(dia, dict):
                # older/newer versions might produce dict
                it = dia.keys()
            else:
                it = dia
            for path in it:
                dotted = dd_path_to_key(path)
                new_val = value_from_path(cur_obj, path)
                diffs.append((k, 'added', dotted, None, new_val, old_obj, cur_obj))
                added += 1

            # dictionary_item_removed
            dir_ = dd.get('dictionary_item_removed', set())
            if isinstance(dir_, dict):
                it = dir_.keys()
            else:
                it = dir_
            for path in it:
                dotted = dd_path_to_key(path)
                old_val = value_from_path(old_obj, path)
                diffs.append((k, 'removed', dotted, old_val, None, old_obj, cur_obj))
                removed += 1

            # iterable_item_added/removed (carry value in mapping)
            for path, val in dd.get('iterable_item_added', {}).items():
                dotted = dd_path_to_key(path)
                diffs.append((k, 'added', dotted, None, val, old_obj, cur_obj))
                added += 1
            for path, val in dd.get('iterable_item_removed', {}).items():
                dotted = dd_path_to_key(path)
                diffs.append((k, 'removed', dotted, val, None, old_obj, cur_obj))
                removed += 1

            # type_changes
            for path, change in dd.get('type_changes', {}).items():
                dotted = dd_path_to_key(path)
                o = change.get('old_value')
                v = change.get('new_value')
                diffs.append((k, 'changed', dotted, o, v, old_obj, cur_obj))
                changed += 1

        self.v_changed.set(f"Changed: {changed}")
        self.v_added.set(f"Added: {added}")
        self.v_removed.set(f"Removed: {removed}")

        self._populate_table(diffs)
        self.btn_export_csv.configure(state='normal')
        self.btn_export_txt.configure(state='normal')

    def _populate_table(self, diffs: List[Tuple[str, str, str, Any, Any, Any, Any]]):
        # remember selection
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        self._tree_meta.clear()

        # Insert
        for cfg, typ, keypath, ov, nv, old_obj, new_obj in diffs:
            tags = [typ]
            if self._row_is_watched(keypath):
                tags.append('watch')
            iid = self.tree.insert('', tk.END, values=(cfg, typ, keypath, self._s(ov), self._s(nv)), tags=tuple(tags))
            self._tree_meta[iid] = RowMeta(cfg, typ, keypath, ov, nv, old_obj, new_obj)

        # Apply current filter
        self._filter_tree()

        # Select first visible
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.see(children[0])
            self.on_tree_select()

    def on_tree_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        meta = self._tree_meta.get(iid)
        if not meta:
            return

        # Inline char diff
        self._show_inline_diff(str(meta.old if meta.old is not None else ""),
                               str(meta.new if meta.new is not None else ""))

        # Full payloads
        self._render_full_payloads(meta.old_obj, meta.new_obj)

        # Highlight lines (synchronous)
        leaf = meta.path.split('.')[-1]
        self.txt_old.update_idletasks()
        self.txt_cur.update_idletasks()

        if meta.typ == 'added':
            self._highlight_line_for_key_value(self.txt_cur, leaf, meta.new)
        elif meta.typ == 'removed':
            self._highlight_line_for_key_value(self.txt_old, leaf, meta.old)
        else:
            self._highlight_line_for_key_value(self.txt_old, leaf, meta.old)
            self._highlight_line_for_key_value(self.txt_cur, leaf, meta.new)

    # ------------- Diff visualization -------------

    def _show_inline_diff(self, old_str: str, new_str: str) -> None:
        self.txt_sel_old.delete('1.0', tk.END)
        self.txt_sel_new.delete('1.0', tk.END)

        a = old_str.split()
        b = new_str.split()
        sm = difflib.SequenceMatcher(a=a, b=b)

        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                self.txt_sel_old.insert(tk.END, ' '.join(a[i1:i2]) + ' ')
                self.txt_sel_new.insert(tk.END, ' '.join(b[j1:j2]) + ' ')
            elif op in ('delete', 'replace'):
                self.txt_sel_old.insert(tk.END, ' '.join(a[i1:i2]) + ' ', 'del')
            if op in ('insert', 'replace'):
                self.txt_sel_new.insert(tk.END, ' '.join(b[j1:j2]) + ' ', 'add')

    def _render_full_payloads(self, old_obj: Any, new_obj: Any) -> None:
        self.txt_old.delete('1.0', tk.END)
        self.txt_cur.delete('1.0', tk.END)
        self.txt_old.insert('1.0', pretty_json(old_obj))
        self.txt_cur.insert('1.0', pretty_json(new_obj))

    def _highlight_line_for_key_value(self, widget: tk.Text, leaf_key: str, value: Any) -> None:
        """Strong highlight that works across themes and formats."""
        try:
            widget.tag_delete("linehit")
        except tk.TclError:
            pass
        widget.tag_configure("linehit", background=UIConfig.COLOR_LINE_HIT_BG, foreground=UIConfig.COLOR_LINE_HIT_FG)
        widget.tag_raise("linehit")

        text = widget.get("1.0", "end-1c")
        if not text.strip():
            return

        # If scalar payload (not JSON object/array), highlight all
        if not text.lstrip().startswith(("{", "[")):
            widget.tag_add("linehit", "1.0", "end-1c")
            widget.see("1.0")
            return

        key = re.escape(str(leaf_key))
        val = "" if value is None else str(value)

        # tolerant JSON value pattern
        json_val_pat = r'("(?:\\.|[^"\\])*"|[-+]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)'

        def _hit(pat: str) -> bool:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if not m:
                return False
            start = f"1.0+{m.start()}c"
            ls = widget.index(start + " linestart")
            le = widget.index(start + " lineend +1c")
            widget.tag_add("linehit", ls, le)
            widget.see(ls)
            return True

        tried: List[str] = []
        if val != "":
            tried += [
                rf'"{key}"\s*:\s*"{re.escape(val)}"',
                rf"'{key}'\s*:\s*'{re.escape(val)}'",
                rf'"{key}"\s*:\s*{re.escape(val)}',
            ]
        for pat in tried:
            if _hit(pat): return

        if _hit(rf'"{key}"\s*:\s*{json_val_pat}'): return
        if _hit(rf'"{key}"\s*:'): return

        # last resort: highlight first line
        widget.tag_add("linehit", "1.0", "2.0")
        widget.see("1.0")

    # ------------- Filtering / watch -------------

    def apply_watchlist(self):
        text = self.ent_watch.get().strip()
        self.watchlist = [w.strip().lower() for w in text.split(',') if w.strip()]
        self._filter_tree()

    def _row_is_watched(self, key_path: str) -> bool:
        if not self.watchlist:
            return True
        lk = key_path.lower()
        return any(w in lk for w in self.watchlist)

    def _filter_tree(self):
        q = (self.search_var.get() or '').strip().lower()
        for iid, meta in self._tree_meta.items():
            show = True
            if q:
                hay = f"{meta.cfgkey} {meta.typ} {meta.path}".lower()
                show = q in hay
            if show and self.only_watch.get():
                show = self._row_is_watched(meta.path)
            if show:
                try:
                    self.tree.reattach(iid, '', 'end')
                except tk.TclError:
                    pass
            else:
                try:
                    self.tree.detach(iid)
                except tk.TclError:
                    pass

    # ------------- Exports -------------

    def on_export_csv(self):
        if not self._tree_meta:
            return
        p = filedialog.asksaveasfilename(
            title='Save visible diffs as CSV',
            defaultextension='.csv',
            filetypes=[('CSV', '*.csv'), ('All files', '*.*')]
        )
        if not p:
            return
        try:
            with open(p, 'w', encoding='utf-8', newline='') as f:
                w = csv.writer(f)
                w.writerow(['Config Key', 'Type', 'Key', 'Old', 'New', 'Watched'])
                for iid in self.tree.get_children():
                    meta = self._tree_meta.get(iid)
                    if not meta:
                        continue
                    w.writerow([meta.cfgkey, meta.typ, meta.path, self._s(meta.old), self._s(meta.new),
                                'YES' if self._row_is_watched(meta.path) else ''])
            messagebox.showinfo('Saved', f'CSV saved to:\n{p}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save CSV:\n{e}')

    def on_export_txt(self):
        if not self._tree_meta:
            return
        p = filedialog.asksaveasfilename(
            title='Save visible diffs as TXT',
            defaultextension='.txt',
            filetypes=[('Text', '*.txt'), ('All files', '*.*')]
        )
        if not p:
            return

        # group visible rows by cfgkey
        grouped: Dict[str, List[RowMeta]] = {}
        for iid in self.tree.get_children():
            meta = self._tree_meta.get(iid)
            if not meta:
                continue
            grouped.setdefault(meta.cfgkey, []).append(meta)

        def indent_block(s: str, n: int) -> str:
            pad = ' ' * n
            return '\n'.join(pad + line if line else '' for line in s.splitlines())

        lines: List[str] = []
        for cfg, items in grouped.items():
            lines.append(f"=== Config Key: {cfg} ===")
            # sections
            sec = {
                'changed': [m for m in items if m.typ == 'changed'],
                'added':   [m for m in items if m.typ == 'added'],
                'removed': [m for m in items if m.typ == 'removed'],
            }
            for typ in ('changed', 'added', 'removed'):
                L = sec[typ]
                if not L:
                    continue
                lines.append(f"\n-- {typ.upper()} ({len(L)}) --")
                for m in L:
                    lines.append(f"Key: {m.path}")
                    if typ == 'changed':
                        lines.append(f"  Old: {self._s(m.old)}")
                        lines.append(f"  New: {self._s(m.new)}")
                        # fragments
                        lines.append("  Fragment (OLD):")
                        try:
                            frag_old = build_fragment_from_path_value(m.path, m.old)
                            lines.append(indent_block(pretty_json(frag_old), 8))
                        except Exception:
                            lines.append("        (fragment error)")
                        lines.append("  Fragment (NEW):")
                        try:
                            frag_new = build_fragment_from_path_value(m.path, m.new)
                            lines.append(indent_block(pretty_json(frag_new), 8))
                        except Exception:
                            lines.append("        (fragment error)")
                    elif typ == 'added':
                        lines.append(f"  New: {self._s(m.new)}")
                        lines.append("  Fragment (NEW):")
                        try:
                            frag_new = build_fragment_from_path_value(m.path, m.new)
                            lines.append(indent_block(pretty_json(frag_new), 8))
                        except Exception:
                            lines.append("        (fragment error)")
                    elif typ == 'removed':
                        lines.append(f"  Old: {self._s(m.old)}")
                        lines.append("  Fragment (OLD):")
                        try:
                            frag_old = build_fragment_from_path_value(m.path, m.old)
                            lines.append(indent_block(pretty_json(frag_old), 8))
                        except Exception:
                            lines.append("        (fragment error)")
            lines.append("\n")

        try:
            with open(p, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            messagebox.showinfo('Saved', f'TXT saved to:\n{p}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save TXT:\n{e}')

    # ------------- Column confirm dialog -------------

    def _confirm_column_mapping(self, headers: List[str], mapping: Dict[str, int],
                                confidence: Dict[str, float]) -> Optional[Dict[str, int]]:
        need = NEEDED_ROLES
        low_conf = [r for r in need if (r not in mapping) or (confidence.get(r, 0) < 0.70)]
        if not low_conf:
            return mapping

        dialog = tk.Toplevel(self)
        dialog.title("Confirm Column Mapping")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        has_very_low = any(confidence.get(r, 0) < 0.4 for r in need)
        row_idx = 0
        if has_very_low:
            warn = ttk.Frame(dialog, relief='solid', borderwidth=1)
            warn.grid(row=row_idx, column=0, columnspan=3, padx=10, pady=(10, 6), sticky='ew')
            ttk.Label(warn, text="⚠ Some columns could not be detected reliably.",
                      foreground='orange', font=('TkDefaultFont', 9, 'bold')).pack(padx=8, pady=8)
            row_idx += 1

        ttk.Label(dialog, text="Please confirm or adjust column mappings:",
                  font=('TkDefaultFont', 10, 'bold')).grid(row=row_idx, column=0, columnspan=3,
                                                           pady=(6, 6), padx=10, sticky='w')
        row_idx += 1

        combos: Dict[str, ttk.Combobox] = {}
        for role in need:
            ttk.Label(dialog, text=f"{role}:").grid(row=row_idx, column=0, padx=10, pady=5, sticky='e')
            combo = ttk.Combobox(dialog, values=headers, width=48, state="readonly")
            if role in mapping and 0 <= mapping[role] < len(headers):
                combo.set(headers[mapping[role]])
            else:
                combo.set(headers[0] if headers else "")
            combo.grid(row=row_idx, column=1, padx=5, pady=5, sticky='w')
            conf_val = confidence.get(role, 0.0)
            color = "green" if conf_val >= 0.7 else ("orange" if conf_val >= 0.4 else "red")
            ttk.Label(dialog, text=f"({conf_val:.0%})", foreground=color).grid(row=row_idx, column=2, padx=5, pady=5, sticky='w')
            row_idx += 1

        result = {"mapping": mapping.copy(), "confirmed": False}

        def on_ok():
            result["mapping"] = {
                role: headers.index(combo.get()) for role, combo in combos.items() if combo.get() in headers
            }
            result["confirmed"] = True
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.grid(row=row_idx, column=0, columnspan=3, pady=10)
        ttk.Button(btns, text="OK", command=on_ok, width=12).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancel", command=on_cancel, width=12).pack(side=tk.LEFT, padx=6)

        # center
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        self.wait_window(dialog)
        return result["mapping"] if result["confirmed"] else None

    # ------------- Progress (threaded) -------------

    def _with_progress_threaded(self, task_fn, title: str, done_cb, determinate: bool = False):
        """Run task_fn in a worker thread with an optional determinate progress."""
        top = tk.Toplevel(self)
        top.title(title)
        top.transient(self)
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", lambda: None)

        ttk.Label(top, text=title).pack(padx=16, pady=(14, 6))
        mode = 'determinate' if determinate else 'indeterminate'
        pb = ttk.Progressbar(top, mode=mode, length=320, maximum=100)
        pb.pack(padx=16, pady=(0, 10))
        if mode == 'indeterminate':
            pb.start(12)

        status_lbl = ttk.Label(top, text="")
        status_lbl.pack(padx=16, pady=(0, 12))

        q_out: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        q_prog: "queue.Queue[Tuple[int, str]]" = queue.Queue()

        def worker():
            try:
                def progress(step, msg):
                    q_prog.put((int(step or 0), str(msg or "")))
                res = task_fn(progress if determinate else None)
                q_out.put(('ok', res))
            except Exception as e:
                q_out.put(('err', e))

        def poll():
            # progress
            try:
                while True:
                    step, msg = q_prog.get_nowait()
                    pb['value'] = max(0, min(100, int(step)))
                    status_lbl.config(text=msg)
                    top.update_idletasks()
            except queue.Empty:
                pass

            # completion
            try:
                status, payload = q_out.get_nowait()
                if mode == 'indeterminate':
                    try:
                        pb.stop()
                    except tk.TclError:
                        pass
                try:
                    top.destroy()
                except tk.TclError:
                    pass
                if status == 'ok':
                    done_cb(payload)
                else:
                    messagebox.showerror("Error", f"Failed to load:\n{payload}")
            except queue.Empty:
                self.after(100, poll)

        threading.Thread(target=worker, daemon=True).start()
        self.after(120, poll)

    # ------------- Small helpers -------------

    def _reset_views(self):
        self.tree.delete(*self.tree.get_children())
        self._tree_meta.clear()
        self.txt_sel_old.delete('1.0', tk.END)
        self.txt_sel_new.delete('1.0', tk.END)
        self.txt_old.delete('1.0', tk.END)
        self.txt_cur.delete('1.0', tk.END)
        self.v_changed.set('Changed: 0')
        self.v_added.set('Added: 0')
        self.v_removed.set('Removed: 0')

    def _s(self, v: Any) -> str:
        if v is None:
            return ''
        if isinstance(v, (dict, list)):
            try:
                return json.dumps(v, ensure_ascii=False)
            except Exception:
                return str(v)
        return str(v)

    def show_shortcuts_help(self):
        messagebox.showinfo("Keyboard Shortcuts",
                            "Keyboard Shortcuts:\n\n"
                            "Ctrl+O - Open file\n"
                            "Ctrl+S - Export CSV (visible rows)\n"
                            "Ctrl+E - Export TXT (visible rows)\n"
                            "Ctrl+F - Focus filter box\n"
                            "F5     - Compare\n"
                            "Esc    - Clear focus")

# -------------------
# Main entrypoint
# -------------------

if __name__ == '__main__':
    app = PayloadDiffViewerApp()
    app.mainloop()