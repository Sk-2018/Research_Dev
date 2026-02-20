from __future__ import annotations

import os
import re
import csv
import json
import queue
import threading
import difflib
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional, Iterable

# Tk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

# Third-party
from deepdiff import DeepDiff
import pandas as pd

# Internal modules
from .file_loader import FileLoader, detect_best_columns, assemble_rows, NEEDED_ROLES
from .json_utils import (
    parse_jsonish_verbose,
    pretty_json,
    dd_path_to_key,
    build_fragment_from_path_value,
)
from .parse_logger import ParseLogger
from .settings import SettingsManager
from .sharepoint import sharepoint_url_to_unc, path_is_accessible
from .ui_config import UIConfig


@dataclass
class RowMeta:
    """One table row meta for a diff item."""
    cfgkey: str
    typ: str          # 'changed' | 'added' | 'removed' | 'type_changed (...)'
    path: str         # friendly dotted path
    old: Any
    new: Any
    old_obj: Any
    new_obj: Any


class SyncedTextPair:
    """
    Synchronize vertical scrolling and provide helpers to highlight and jump.
    Works by wiring each Text widget's yscrollcommand to update the other.
    """

    def __init__(self, left: tk.Text, right: tk.Text, left_vsb: ttk.Scrollbar, right_vsb: ttk.Scrollbar):
        self.left = left
        self.right = right
        self.left_vsb = left_vsb
        self.right_vsb = right_vsb
        self._lock = False  # prevent feedback loops

        # Wrap the yscrollcommand to get first/last fractions and move the peer.
        self.left.configure(yscrollcommand=self._left_yscroll)
        self.right.configure(yscrollcommand=self._right_yscroll)

        # Scrollbars control only their own widget; programmatically we sync peers.
        self.left_vsb.configure(command=self.left.yview)
        self.right_vsb.configure(command=self.right.yview)

        # Mouse wheel sync
        for w in (self.left, self.right):
            w.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
            w.bind("<Button-4>", self._on_wheel_up, add="+")     # some Tk builds
            w.bind("<Button-5>", self._on_wheel_down, add="+")
            w.bind("<Shift-MouseWheel>", self._on_mouse_wheel, add="+")
            w.bind("<Control-MouseWheel>", self._on_mouse_wheel, add="+")
            w.bind("<Command-MouseWheel>", self._on_mouse_wheel, add="+")

    def _left_yscroll(self, first: str, last: str) -> None:
        self.left_vsb.set(first, last)
        if self._lock:
            return
        try:
            self._lock = True
            self.right.yview_moveto(float(first))
        finally:
            self._lock = False

    def _right_yscroll(self, first: str, last: str) -> None:
        self.right_vsb.set(first, last)
        if self._lock:
            return
        try:
            self._lock = True
            self.left.yview_moveto(float(first))
        finally:
            self._lock = False

    def _on_mouse_wheel(self, event) -> str:
        # Tk reports positive delta on wheel up in Windows
        lines = -1 * int(event.delta / 120) if event.delta else 0
        if lines:
            self.left.yview_scroll(lines, "units")
            self.right.yview_scroll(lines, "units")
        return "break"

    def _on_wheel_up(self, _event) -> str:
        self.left.yview_scroll(-1, "units")
        self.right.yview_scroll(-1, "units")
        return "break"

    def _on_wheel_down(self, _event) -> str:
        self.left.yview_scroll(1, "units")
        self.right.yview_scroll(1, "units")
        return "break"

    def jump_both_to_fraction(self, frac: float) -> None:
        frac = max(0.0, min(1.0, float(frac)))
        self.left.yview_moveto(frac)
        self.right.yview_moveto(frac)


class App(tk.Tk):
    """Payload Diff Viewer"""

    def __init__(self):
        super().__init__()
        self.title("Payload Diff Viewer (Config Name -> Current vs Old)")
        self.geometry(f"{UIConfig.WINDOW_W}x{UIConfig.WINDOW_H}")
        self.minsize(UIConfig.MIN_W, UIConfig.MIN_H)

        # State
        self.parse_logger = ParseLogger()               # <-- create here
        self.loader = FileLoader(self.parse_logger)     # <-- pass to FileLoader
        self.settings = SettingsManager()

        self.rows: List[Dict[str, str]] = []
        self.by_name: Dict[str, List[Dict[str, str]]] = {}
        self._last_open_dir: Optional[str] = None

        # Watch & filter
        self.watchlist: List[str] = []
        self.only_watch = tk.BooleanVar(value=False)
        self.arrays_as_sets = tk.BooleanVar(value=False)
        self.auto_compare = tk.BooleanVar(value=False)

        # UI bits
        self._tree_meta: Dict[str, RowMeta] = {}
        self.search_var = tk.StringVar()

        # Build + bindings
        self._build_ui()
        self._bind_shortcuts()

    # ==================
    # UI construction
    # ==================

    def _build_ui(self) -> None:
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

        # Top controls
        top = ttk.Frame(self); top.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(top, text='Open…', command=self.on_open).pack(side=tk.LEFT)

        ttk.Label(top, text='Config Name:').pack(side=tk.LEFT, padx=(12, 4))
        self.cmb_name = ttk.Combobox(top, state='disabled', width=36)
        self.cmb_name.pack(side=tk.LEFT)
        self.cmb_name.bind('<<ComboboxSelected>>', self.on_name_selected)

        ttk.Label(top, text='Config Keys:').pack(side=tk.LEFT, padx=(12, 4))
        self.lst_keys = tk.Listbox(top, selectmode=tk.EXTENDED, width=38, height=6, exportselection=False)
        self.lst_keys.pack(side=tk.LEFT)
        self.lst_keys.configure(state=tk.DISABLED)
        self.lst_keys.bind('<<ListboxSelect>>', lambda e: self._maybe_auto_compare())

        btn_frame = ttk.Frame(top); btn_frame.pack(side=tk.LEFT, padx=(12, 0), fill=tk.Y)
        self.btn_compare = ttk.Button(btn_frame, text='Compare (F5)', state='disabled', command=self.on_compare)
        self.btn_compare.pack(pady=(0, 2))
        self.btn_clear = ttk.Button(btn_frame, text='Clear Results', state='disabled', command=self._reset_views)
        self.btn_clear.pack()

        self.chk_auto = ttk.Checkbutton(btn_frame, text='Auto compare', variable=self.auto_compare)
        self.chk_auto.pack(pady=(6, 0))

        self.btn_export_csv = ttk.Button(top, text='Export CSV', state='disabled', command=self.on_export_csv)
        self.btn_export_csv.pack(side=tk.LEFT, padx=(6, 0))
        self.btn_export_txt = ttk.Button(top, text='Export TXT', state='disabled', command=self.on_export_txt)
        self.btn_export_txt.pack(side=tk.LEFT, padx=(6, 0))

        self.lbl = ttk.Label(self, text='Open a CSV/Excel file to begin.')
        self.lbl.pack(anchor='w', padx=12)

        # Options
        opt = ttk.Frame(self); opt.pack(fill=tk.X, padx=10, pady=(2, 6))
        ttk.Label(opt, text='Arrays:').pack(side=tk.LEFT)
        ttk.Radiobutton(opt, text='by index', variable=self.arrays_as_sets, value=False, command=self.on_compare)\
            .pack(side=tk.LEFT, padx=(4, 12))
        ttk.Radiobutton(opt, text='as set (ignore order)', variable=self.arrays_as_sets, value=True, command=self.on_compare)\
            .pack(side=tk.LEFT)

        ttk.Label(opt, text='  Watch keys:').pack(side=tk.LEFT, padx=(14, 4))
        self.ent_watch = ttk.Entry(opt, width=64); self.ent_watch.pack(side=tk.LEFT)
        self.ent_watch.insert(0, UIConfig.DEFAULT_WATCHLIST)
        ttk.Checkbutton(opt, text='Only watch', variable=self.only_watch, command=self._filter_tree)\
            .pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(opt, text='Apply', command=self.apply_watchlist).pack(side=tk.LEFT, padx=(8, 0))

        # Filter row + counts
        flt = ttk.Frame(self); flt.pack(fill=tk.X, padx=10, pady=(0, 6))
        ttk.Label(flt, text='Filter:').pack(side=tk.LEFT)
        self.filter_entry = ttk.Entry(flt, textvariable=self.search_var, width=40); self.filter_entry.pack(side=tk.LEFT, padx=8)
        ttk.Button(flt, text='Clear', command=lambda: self.search_var.set('')).pack(side=tk.LEFT)
        self.search_var.trace_add('write', lambda *_: self._filter_tree())

        self.v_changed = tk.StringVar(value='Changed: 0')
        self.v_added   = tk.StringVar(value='Added: 0')
        self.v_removed = tk.StringVar(value='Removed: 0')
        ttk.Label(flt, textvariable=self.v_changed, foreground='#7a5a00').pack(side=tk.LEFT, padx=(20, 12))
        ttk.Label(flt, textvariable=self.v_added, foreground='#096b00').pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(flt, textvariable=self.v_removed, foreground='#a00000').pack(side=tk.LEFT)

        # Diff table
        ftable = ttk.Frame(self); ftable.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 8))
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
        ftable.rowconfigure(0, weight=1); ftable.columnconfigure(0, weight=1)

        # Row color tags
        self.tree.tag_configure('changed', background=UIConfig.COLOR_CHANGED)
        self.tree.tag_configure('added',   background=UIConfig.COLOR_ADDED)
        self.tree.tag_configure('removed', background=UIConfig.COLOR_REMOVED)
        self.tree.tag_configure('type_changed', background=UIConfig.COLOR_CHANGED)  # NEW

        # Watch tag
        default_font = tkfont.nametofont("TkDefaultFont")
        bold_font = tkfont.Font(**default_font.configure()); bold_font.configure(weight='bold')
        self.tree.tag_configure('watch', foreground='#0b5bb5', font=bold_font)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # Lower panes
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL); paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        fmid = ttk.LabelFrame(paned, text='Selected Field - Inline Diff'); paned.add(fmid, weight=1)
        left = ttk.Frame(fmid); left.grid(row=1, column=0, sticky='nsew', padx=(0, 6))
        right = ttk.Frame(fmid); right.grid(row=1, column=1, sticky='nsew', padx=(6, 0))
        fmid.columnconfigure(0, weight=1); fmid.columnconfigure(1, weight=1); fmid.rowconfigure(1, weight=1)

        self.lbl_inline_old = ttk.Label(left, text='OLD'); self.lbl_inline_old.pack(anchor='w')
        self.txt_sel_old = tk.Text(left, wrap='word', height=getattr(UIConfig, "INLINE_ROWS", 8), font=("Courier New", 9))
        self.txt_sel_old.pack(fill=tk.BOTH, expand=True); self.txt_sel_old.tag_configure('del', background='#ffcccc')

        self.lbl_inline_new = ttk.Label(right, text='CURRENT'); self.lbl_inline_new.pack(anchor='w')
        self.txt_sel_new = tk.Text(right, wrap='word', height=getattr(UIConfig, "INLINE_ROWS", 8), font=("Courier New", 9))
        self.txt_sel_new.pack(fill=tk.BOTH, expand=True); self.txt_sel_new.tag_configure('add', background='#c2f0c2')

        fbot = ttk.Frame(paned); paned.add(fbot, weight=2)
        jl = ttk.LabelFrame(fbot, text='OLD Payload (Full JSON)'); jl.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        jr = ttk.LabelFrame(fbot, text='CURRENT Payload (Full JSON)'); jr.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        fbot.columnconfigure(0, weight=1); fbot.columnconfigure(1, weight=1); fbot.rowconfigure(0, weight=1)

        self.txt_old = tk.Text(jl, wrap='none', font=("Courier New", 9))
        sc1y = ttk.Scrollbar(jl, orient='vertical', command=self.txt_old.yview)
        sc1x = ttk.Scrollbar(jl, orient='horizontal', command=self.txt_old.xview)
        self.txt_old.configure(yscrollcommand=sc1y.set, xscrollcommand=sc1x.set)
        self.txt_old.pack(fill=tk.BOTH, expand=True); sc1y.pack(side=tk.RIGHT, fill=tk.Y); sc1x.pack(side=tk.BOTTOM, fill=tk.X)

        self.txt_cur = tk.Text(jr, wrap='none', font=("Courier New", 9))
        sc2y = ttk.Scrollbar(jr, orient='vertical', command=self.txt_cur.yview)
        sc2x = ttk.Scrollbar(jr, orient='horizontal', command=self.txt_cur.xview)
        self.txt_cur.configure(yscrollcommand=sc2y.set, xscrollcommand=sc2x.set)
        self.txt_cur.pack(fill=tk.BOTH, expand=True); sc2y.pack(side=tk.RIGHT, fill=tk.Y); sc2x.pack(side=tk.BOTTOM, fill=tk.X)

        # Synchronize vertical scrolling between the full panes
        self.sync_pair = SyncedTextPair(self.txt_old, self.txt_cur, sc1y, sc2y)

    def _bind_shortcuts(self):
        self.bind_all('<Control-o>', lambda e: self.on_open())
        self.bind_all('<Control-s>', lambda e: self.on_export_csv())
        self.bind_all('<Control-e>', lambda e: self.on_export_txt())
        self.bind_all('<Control-f>', lambda e: (self.filter_entry.focus_set(), self.filter_entry.select_range(0, tk.END)))
        self.bind_all('<F5>', lambda e: self.on_compare())
        self.bind_all('<Escape>', lambda e: self.focus_set())

    # ===============
    # File handling
    # ===============

    def on_open(self):
        initial = self._get_initial_open_dir()
        p = filedialog.askopenfilename(
            title="Select CSV/TSV/TXT/XLSX/XLS",
            initialdir=initial,
            filetypes=[
                ("All supported", "*.csv *.tsv *.txt *.xlsx *.xls"),
                ("Excel", "*.xlsx *.xls"),
                ("CSV/TSV/TXT", "*.csv *.tsv *.txt"),
                ("All files", "*.*"),
            ]
        )
        if not p:
            return

        ok, why = self.loader.validate_file(p)
        if not ok:
            messagebox.showerror("File Error", why)
            return

        self._last_open_dir = os.path.dirname(p)

        def load_task(progress_cb=None):
            # Refactored: Use the pandas-based load_any from file_loader
            # It returns (df, roles, problems, confidence)
            return self.loader.load_any(p)

        def on_loaded(result: Tuple[pd.DataFrame, Dict[str, str], List[str], Dict[str, float]]):
            df, mapping, problems, conf = result

            # Log any non-fatal problems
            for prob in problems:
                self.parse_logger.log(prob, level='warning', context=f"File: {os.path.basename(p)}")

            if df is None or df.empty:
                messagebox.showwarning('No Data', 'File appears to be empty or has no data rows.')
                return

            headers = list(df.columns)
            missing = [r for r in NEEDED_ROLES if not mapping.get(r)]
            
            if missing:
                # Pass the headers and the auto-detected mapping and confidence
                mapping2 = self._confirm_column_mapping(headers, mapping, conf)
                if not mapping2:
                    messagebox.showinfo("Cancelled", "Column mapping was not confirmed.")
                    return
                mapping = mapping2 # User confirmed or changed the mapping

            # Refactored: Use the pandas-based assemble_rows
            self.rows = assemble_rows(df, mapping)
            self._finalize_load()

        self._with_progress_threaded(
            load_task,
            title="Loading file...",
            done_cb=on_loaded,
            determinate=False  # load_any doesn't provide chunked progress
        )

    def _get_initial_open_dir(self) -> Optional[str]:
        d = self.settings.get("default_open_dir", None)
        if d:
            if d.lower().startswith("http"):
                unc = sharepoint_url_to_unc(d)
                if unc and path_is_accessible(unc):
                    return unc
            elif os.path.isdir(d):
                return d
        if self._last_open_dir and os.path.isdir(self._last_open_dir):
            return self._last_open_dir
        return None

    def _finalize_load(self):
        self.by_name.clear()
        
        # Close the old parse log window, if any
        if self.parse_logger:
            self.parse_logger.close()
            
        self.parse_logger = ParseLogger()  # reset logger for new file
        self.loader.parse_logger = self.parse_logger  # keep loader using same logger

        for r in self.rows:
            # assemble_rows now uses the standard role names
            nm = (r.get('config_name') or '').strip()
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

        self.lbl.configure(text=f"Loaded {len(self.rows):,} valid rows. Select a Config Name to begin.")
        self._reset_views()

    def on_name_selected(self, _evt=None):
        n = self.cmb_name.get().strip()
        self._reset_views()
        self.btn_compare.configure(state='disabled')

        self.lst_keys.delete(0, tk.END)
        if not n:
            self.lst_keys.configure(state=tk.DISABLED)
            return

        # Use standard role 'config_key'
        keys = sorted({r['config_key'].strip() for r in self.by_name.get(n, []) if r.get('config_key', '').strip()})
        for k in keys:
            self.lst_keys.insert(tk.END, k)

        if keys:
            self.lst_keys.configure(state=tk.NORMAL)
            self.lst_keys.select_set(0, tk.END)  # select all by default
            self.btn_compare.configure(state='normal')
            self._maybe_auto_compare()
        else:
            self.lst_keys.configure(state=tk.DISABLED)

    def _get_selected_config_keys(self) -> List[str]:
        sel_indices = self.lst_keys.curselection()
        if not sel_indices:
            messagebox.showwarning('Select Keys', 'Please select one or more Config Keys to compare.')
            return []
        return [self.lst_keys.get(i) for i in sel_indices]

    def _get_rows_for_keys(self, name: str, keys: List[str]) -> Iterable[Dict[str, str]]:
        # Use standard role 'config_key'
        return [r for r in self.by_name.get(name, []) if r.get('config_key', '').strip() in keys]

    # ==========================
    # Comparison / diff engine
    # ==========================

    def on_compare(self):
        name = self.cmb_name.get().strip()
        selected_keys = self._get_selected_config_keys()
        if not name or not selected_keys:
            return

        # --- Refactored to run in a thread ---
        self._selected_path_cache = self._get_selected_diff_path()  # Cache selection
        rows_to_compare = list(self._get_rows_for_keys(name, selected_keys))
        ignore_order = self.arrays_as_sets.get()

        def compare_task(_progress_cb=None):
            # This runs in a thread
            return self._compute_all_diffs(rows_to_compare, name, ignore_order)

        self._with_progress_threaded(
            compare_task,
            title="Comparing payloads...",
            done_cb=self._on_compare_finished,
            determinate=False  # DeepDiff doesn't provide progress
        )

    def _on_compare_finished(self, result: Tuple[List[RowMeta], Dict[str, int]]):
        # This runs on the main thread when the task is done
        diffs, stats = result

        if len(diffs) > UIConfig.DIFF_DISPLAY_LIMIT:
            msg = (f"The comparison generated {len(diffs):,} differences. "
                   f"Displaying them all may slow down the UI.\n\n"
                   f"Do you want to display only the first {UIConfig.DIFF_DISPLAY_LIMIT:,} results?")
            if messagebox.askyesno("Large Result Set", msg):
                diffs = diffs[:UIConfig.DIFF_DISPLAY_LIMIT]
            else:
                return  # User cancelled

        self.v_changed.set(f"Changed: {stats['changed']}")
        self.v_added.set(f"Added: {stats['added']}")
        self.v_removed.set(f"Removed: {stats['removed']}")

        self._populate_table(diffs)
        self._try_restore_selection(getattr(self, "_selected_path_cache", None))  # Use cache

        self.btn_clear.configure(state='normal')
        self.btn_export_csv.configure(state='normal')
        self.btn_export_txt.configure(state='normal')

    def _compute_all_diffs(self, rows_to_compare: Iterable[Dict[str, str]], 
                             name: str, ignore_order: bool) -> Tuple[List[RowMeta], Dict[str, int]]:
        all_diffs: List[RowMeta] = []
        stats = {'changed': 0, 'added': 0, 'removed': 0}

        for row in rows_to_compare:
            # Use standard keys from assemble_rows
            k = row['config_key']
            old_s = row['old_json']
            cur_s = row['current_json']
            
            old_obj, err1 = parse_jsonish_verbose(old_s)
            cur_obj, err2 = parse_jsonish_verbose(cur_s)
            
            if err1:
                self.parse_logger.log(f"[{name}/{k}] OLD: {err1}", context=old_s[:200])
            if err2:
                self.parse_logger.log(f"[{name}/{k}] CURRENT: {err2}", context=cur_s[:200])

            dd = DeepDiff(old_obj, cur_obj, ignore_order=ignore_order, verbose_level=2)

            for diff_type, changes in dd.items():
                if diff_type == 'values_changed':
                    for path, change in changes.items():
                        all_diffs.append(RowMeta(k, 'changed', dd_path_to_key(path),
                                                 change['old_value'], change['new_value'],
                                                 old_obj, cur_obj))
                        stats['changed'] += 1
                elif diff_type in ('dictionary_item_added', 'iterable_item_added'):
                    for path, val in changes.items():
                        all_diffs.append(RowMeta(k, 'added', dd_path_to_key(path),
                                                 None, val, old_obj, cur_obj))
                        stats['added'] += 1
                elif diff_type in ('dictionary_item_removed', 'iterable_item_removed'):
                    for path, val in changes.items():
                        all_diffs.append(RowMeta(k, 'removed', dd_path_to_key(path),
                                                 val, None, old_obj, cur_obj))
                        stats['removed'] += 1
                elif diff_type == 'type_changes':
                    # NEW: label type-only differences clearly
                    for path, change in changes.items():
                        old_v, new_v = change['old_value'], change['new_value']
                        old_t, new_t = type(old_v).__name__, type(new_v).__name__
                        all_diffs.append(RowMeta(
                            k,
                            f'type_changed ({old_t}→{new_t})',
                            dd_path_to_key(path),
                            old_v, new_v,
                            old_obj, cur_obj
                        ))
                        stats['changed'] += 1
        return all_diffs, stats

    # ==========================
    # Table population / filter
    # ==========================

    def _populate_table(self, diffs: List[RowMeta]):
        self.tree.delete(*self.tree.get_children())
        self._tree_meta.clear()

        for meta in diffs:
            tags: List[str] = []
            if isinstance(meta.typ, str) and meta.typ.startswith('type_changed'):
                tags.append('type_changed')
            else:
                tags.append(meta.typ)  # changed/added/removed

            if self._row_is_watched(meta.path):
                tags.append('watch')

            iid = self.tree.insert(
                '',
                tk.END,
                values=(meta.cfgkey, meta.typ, meta.path, self._s(meta.old), self._s(meta.new)),
                tags=tuple(tags)
            )
            self._tree_meta[iid] = meta

        self._filter_tree()
        if not self.tree.selection():
            children = self.tree.get_children()
            if children:
                self.tree.selection_set(children[0])
                self.tree.focus(children[0])
                self.tree.see(children[0])

    def _filter_tree(self, *_):
        query = self.search_var.get().strip().lower()
        children = self.tree.get_children('')
        if not children:
            return

        # Re-attach everything first (cheap)
        for iid in children:
            self.tree.reattach(iid, '', 'end')

        for iid, meta in self._tree_meta.items():
            is_visible = True
            if query:
                haystack = f"{meta.cfgkey} {meta.typ} {meta.path} {self._s(meta.old)} {self._s(meta.new)}".lower()
                is_visible = query in haystack
            if is_visible and self.only_watch.get():
                is_visible = self._row_is_watched(meta.path)
            if not is_visible:
                self.tree.detach(iid)

    def apply_watchlist(self):
        text = self.ent_watch.get().strip()
        self.watchlist = [w.strip().lower() for w in text.split(',') if w.strip()]
        self._filter_tree()
        self.on_compare()  # re-run compare to apply watch tags

    def _row_is_watched(self, key_path: str) -> bool:
        if not self.watchlist:
            return False
        lk = key_path.lower()
        return any(w in lk for w in self.watchlist)

    # ==========================
    # Selection handlers
    # ==========================

    def on_tree_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        meta = self._tree_meta.get(sel[0])
        if not meta:
            return

        # Update inline panes (show quotes via _s)
        self._show_inline_diff(
            self._s(meta.old if meta.old is not None else ""),
            self._s(meta.new if meta.new is not None else "")
        )

        # Update full JSON panes
        self._render_full_payloads(meta.old_obj, meta.new_obj)

        # Show types in headers
        try:
            old_t = 'NoneType' if meta.old is None else type(meta.old).__name__
            new_t = 'NoneType' if meta.new is None else type(meta.new).__name__
            self.lbl_inline_old.config(text=f'OLD  [type: {old_t}]')
            self.lbl_inline_new.config(text=f'CURRENT  [type: {new_t}]')
        except Exception:
            pass

        # Highlight in both panes
        leaf_key = meta.path.split('.')[-1].split('[')[0]
        self.after(50, lambda: self._highlight_in_panes(meta, leaf_key))

    def _highlight_in_panes(self, meta: RowMeta, leaf_key: str):
        if meta.typ.startswith('changed') or meta.typ.startswith('type_changed') or meta.typ == 'removed':
            self._highlight_line_for_key_value(self.txt_old, leaf_key, meta.old)
        if meta.typ.startswith('changed') or meta.typ.startswith('type_changed') or meta.typ == 'added':
            self._highlight_line_for_key_value(self.txt_cur, leaf_key, meta.new)

    # ==========================
    # Inline + full panes
    # ==========================

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
        tag = "linehit"
        widget.tag_remove(tag, "1.0", "end")
        widget.tag_configure(tag, background=UIConfig.COLOR_LINE_HIT_BG, foreground=UIConfig.COLOR_LINE_HIT_FG)

        text = widget.get("1.0", "end-1c")
        if not text.strip():
            return

        key_pat = re.escape(f'"{leaf_key}"')
        match = None

        # --- Enhancement: Only try full value match for scalars ---
        if not isinstance(value, (dict, list)):
            try:
                val_str = json.dumps(value)
            except Exception:
                val_str = str(value) if value is not None else "null"

            # This regex will only match scalars in a pretty_json output
            full_pat = re.compile(f"{key_pat}\\s*:\\s*{re.escape(val_str)}")
            match = full_pat.search(text)

        if not match:
            # Fallback: key-only (will be used for all lists/dicts)
            key_only_pat = re.compile(key_pat)
            match = key_only_pat.search(text)

        if match:
            start_pos = f"1.0 + {match.start()} chars"
            line_start = widget.index(f"{start_pos} linestart")
            line_end = widget.index(f"{start_pos} lineend + 1 char")
            widget.tag_add(tag, line_start, line_end)
            widget.see(line_start)
            # Sync both panes to the same relative position
            try:
                first, _ = widget.yview()
                self.sync_pair.jump_both_to_fraction(first)
            except Exception:
                pass
        else:
            # As a last resort, just highlight the first line
            widget.tag_add(tag, "1.0", "2.0")


    # ==========================
    # Export
    # ==========================

    def on_export_csv(self):
        if not self._tree_meta:
            return
        p = filedialog.asksaveasfilename(title='Save Visible Diffs as CSV', defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if not p:
            return
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
        if not self._tree_meta:
            return
        p = filedialog.asksaveasfilename(title='Save Visible Diffs as TXT', defaultextension='.txt', filetypes=[('Text', '*.txt')])
        if not p:
            return

        grouped: Dict[str, List[RowMeta]] = {}
        for iid in self.tree.get_children():
            meta = self._tree_meta[iid]
            grouped.setdefault(meta.cfgkey, []).append(meta)

        lines = []
        for cfgkey, items in grouped.items():
            lines.append(f"=== Config Key: {cfgkey} ===")
            for typ in ('changed', 'type_changed', 'added', 'removed'):
                diffs_of_type = [m for m in items if (m.typ == typ or (typ == 'type_changed' and str(m.typ).startswith('type_changed')))]
                if not diffs_of_type:
                    continue
                lines.append(f"\n-- {typ.upper()} ({len(diffs_of_type)}) --")
                for m in diffs_of_type:
                    lines.append(f"Key: {m.path}")
                    if str(m.typ).startswith('type_changed') or m.typ == 'changed':
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
            lines.append("\n" + "=" * 60 + "\n")

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

    # ==========================
    # Column confirm dialog
    # ==========================

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
        # Use headers list for combobox values
        combo_values = [""] + sorted(headers) # Add "" for optional
        
        for i, role in enumerate(NEEDED_ROLES, 1):
            ttk.Label(dialog, text=f"{role}:").grid(row=i, column=0, padx=10, pady=5, sticky='e')
            combo = ttk.Combobox(dialog, values=combo_values, width=48, state="readonly")
            
            # 'mapping' from file_loader is {role: col_name}
            if mapping.get(role):
                combo.set(mapping[role])
            else:
                combo.set("") # Set to blank if not found
                
            combo.grid(row=i, column=1, padx=5, pady=5, sticky='w')
            combos[role] = combo

            conf_val = confidence.get(role, 0.0)
            color = "green" if conf_val >= 0.7 else ("orange" if conf_val >= 0.4 else "red")
            ttk.Label(dialog, text=f"({conf_val:.0%})", foreground=color).grid(row=i, column=2, padx=5, pady=5, sticky='w')

        result = {"mapping": None}

        def on_ok():
            # Convert back from col_name to role
            new_mapping = {role: combo.get() for role, combo in combos.items() if combo.get()}
            
            # Check for duplicates
            seen_cols = {}
            for role, col in new_mapping.items():
                if col in seen_cols:
                    messagebox.showerror("Duplicate Columns", 
                                         f"Column '{col}' is mapped to both '{role}' and '{seen_cols[col]}'.\n"
                                         "Each role must be mapped to a unique column.", 
                                         parent=dialog)
                    return
                seen_cols[col] = role

            # Ensure all required roles are present
            missing_req = [r for r in NEEDED_ROLES if not new_mapping.get(r)]
            if missing_req:
                messagebox.showerror("Missing Roles",
                                     f"The following required roles are not mapped:\n"
                                     f"{', '.join(missing_req)}",
                                     parent=dialog)
                return

            result["mapping"] = new_mapping
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.grid(row=len(NEEDED_ROLES) + 1, column=0, columnspan=3, pady=10)
        ttk.Button(btns, text="OK", command=on_ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=6)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        self.wait_window(dialog)
        return result["mapping"]

    # ==========================
    # Progress (threaded)
    # ==========================

    def _with_progress_threaded(self, task_fn, title: str, done_cb, determinate: bool = False):
        top = tk.Toplevel(self)
        top.title(title)
        top.transient(self)
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent closing

        ttk.Label(top, text=title, font=('TkDefaultFont', 10)).pack(padx=20, pady=(15, 6))
        pb = ttk.Progressbar(top, mode='determinate' if determinate else 'indeterminate', length=350, maximum=100)
        pb.pack(padx=20, pady=(0, 10))
        if not determinate:
            pb.start(10)

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
                if not determinate:
                    pb.stop()
                top.destroy()
                if status == 'ok':
                    done_cb(payload)
                else:
                    messagebox.showerror("Error", f"An error occurred during loading:\n{payload}")
            except queue.Empty:
                self.after(100, poll)

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, poll)

    # ==========================
    # Small helpers
    # ==========================

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
        self.search_var.set('')

        self.btn_clear.configure(state='disabled')
        self.btn_export_csv.configure(state='disabled')
        self.btn_export_txt.configure(state='disabled')

    def _s(self, v: Any) -> str:
        """Compact, human-friendly scalar for grid cells. Shows quotes for strings."""
        if v is None:
            return 'null'
        if isinstance(v, str):
            return f'"{v}"'
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            s = format(v, 'f')
            return s.rstrip('0').rstrip('.') if '.' in s else s
        if isinstance(v, (dict, list)):
            try:
                return json.dumps(v, ensure_ascii=False)
            except TypeError:
                return str(v)
        return str(v)

    def _get_selected_diff_path(self) -> Optional[str]:
        if not self.tree.selection():
            return None
        meta = self._tree_meta.get(self.tree.selection()[0])
        return meta.path if meta else None

    def _try_restore_selection(self, path_to_select: Optional[str]):
        if not path_to_select:
            return
        for iid, meta in self._tree_meta.items():
            if meta.path == path_to_select:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                break

    def _maybe_auto_compare(self) -> None:
        if not self.auto_compare.get():
            return
        name = (self.cmb_name.get() or "").strip()
        sel = self.lst_keys.curselection()
        if name and sel:
            if getattr(self, "_auto_compare_after_id", None):
                try:
                    self.after_cancel(self._auto_compare_after_id)
                except Exception:
                    pass
            self._auto_compare_after_id = self.after(150, self.on_compare)

    def show_shortcuts_help(self):
        messagebox.showinfo(
            "Keyboard Shortcuts",
            "Ctrl+O : Open file\n"
            "Ctrl+S : Export visible rows to CSV\n"
            "Ctrl+E : Export visible rows to TXT\n"
            "Ctrl+F : Focus the filter box\n\n"
            "F5     : Run comparison on selected keys\n"
            "Esc    : Remove focus from the current widget"
        )