# -*- coding: utf-8 -*-
"""
PayloadDiffViewer_PERFECT_v2.py - Synchronized Scrolling + Blue Highlights

FIXED:
✓ Synchronized scrolling between OLD and CURRENT payloads
✓ Blue (#87CEEB) highlighting instead of yellow
✓ Multiple highlights per config (all changes shown)
✓ Perfect scroll sync with mousewheel and scrollbar
"""

import os
import sys
import json
import logging
import re
import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, font as tkfont
from concurrent.futures import ThreadPoolExecutor
import threading

import pandas as pd
import numpy as np
from deepdiff import DeepDiff

try:
    from ultra_fast_loader import UltraFastLoader
except ImportError:
    print("ERROR: ultra_fast_loader.py required!")
    sys.exit(1)

Path('logs').mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/viewer_perfect.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    """Configuration."""
    max_records: int = 10_000_000
    max_workers: int = min(8, os.cpu_count() or 4)
    page_size: int = 1000
    
    # Color scheme - BLUE HIGHLIGHTS
    COLOR_CHANGED_BG: str = "#FFF5CC"      # Yellow for changed rows in tree
    COLOR_ADDED_BG: str = "#E6FFED"        # Green for added rows
    COLOR_REMOVED_BG: str = "#FFECEC"      # Red for removed rows
    COLOR_DIFF_OLD: str = "#FFB6B6"        # Red for deleted text (inline)
    COLOR_DIFF_NEW: str = "#B6FFB6"        # Green for added text (inline)
    COLOR_HIGHLIGHT_LINE: str = "#87CEEB"  # BLUE for line highlighting (changed from yellow)
    COLOR_EQUAL: str = "#E8E8E8"           # Gray for equal text


CONFIG = AppConfig()


@dataclass
class RowMeta:
    """Row metadata."""
    cfgkey: str
    typ: str
    path: str
    old: Any
    new: Any


def dd_path_to_key(p: str) -> str:
    """Convert DeepDiff path to readable key."""
    if not p:
        return p
    p = p.replace("root", "")
    p = re.sub(r"\['([^']+)'\]", r".\1", p)
    p = re.sub(r"\[(\d+)\]", r"[\1]", p)
    p = p.lstrip(".")
    return p


def value_from_path(obj: Any, ddpath: str) -> Any:
    """Extract value using DeepDiff path."""
    dotted = dd_path_to_key(ddpath)
    tokens = [t for t in re.split(r"\.", dotted) if t]
    cur = obj
    try:
        for t in tokens:
            if t.startswith("[") and t.endswith("]"):
                idx = int(t[1:-1])
                cur = cur[idx]
            else:
                cur = cur[t]
        return cur
    except (KeyError, IndexError, TypeError):
        return None


def pretty_json(obj: Any) -> str:
    """Pretty JSON."""
    if obj is None:
        return ""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except:
        return str(obj)


class PerfectDiffViewer(tk.Tk):
    """Perfect viewer with synchronized scrolling."""
    
    def __init__(self):
        super().__init__()
        self.title("Perfect Payload Diff - Synchronized Scrolling + Blue Highlights")
        self.geometry("1700x1000")
        
        try:
            self.state('zoomed')
        except:
            pass
        
        # Data
        self.df: Optional[pd.DataFrame] = None
        self.filtered_df: Optional[pd.DataFrame] = None
        self.loader = UltraFastLoader(max_workers=CONFIG.max_workers)
        self.full_payloads_cache: Dict[str, tuple] = {}
        self.tree_meta: Dict[str, RowMeta] = {}
        self.config_diffs: Dict[str, List[RowMeta]] = {}  # config_name -> list of diffs
        
        # Pagination
        self.current_page = 0
        self.total_pages = 0
        self.filter_active = False
        
        # UI
        self.tree = None
        self.progress_bar = None
        self.status_label = None
        self.txt_old = None
        self.txt_new = None
        self.txt_inline_old = None
        self.txt_inline_new = None
        
        # Fonts
        self.mono_font = tkfont.Font(family="Courier New", size=9)
        self.bold_font = tkfont.Font(family="Arial", size=10, weight="bold")
        
        self._build_ui()
        
        # Shortcuts
        self.bind('<Control-o>', lambda e: self.load_file())
        self.bind('<Control-f>', lambda e: self.show_filter())
        self.bind('<Control-e>', lambda e: self.export_csv())
        self.bind('<F5>', lambda e: self.refresh_page())
        
        if len(sys.argv) > 1:
            self.after(100, lambda: self.load_file(sys.argv[1]))
    
    def _build_ui(self):
        """Build UI with synchronized scrolling."""
        
        # Toolbar
        toolbar = ttk.Frame(self, relief='raised')
        toolbar.pack(side='top', fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="📁 Open (Ctrl+O)", command=self.load_file, width=15).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔍 Filter (Ctrl+F)", command=self.show_filter, width=15).pack(side='left', padx=2)
        ttk.Button(toolbar, text="💾 Export (Ctrl+E)", command=self.export_csv, width=15).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔄 Refresh (F5)", command=self.refresh_page, width=15).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📊 Stats", command=self.show_stats, width=12).pack(side='left', padx=2)
        
        # Status
        status_frame = ttk.Frame(self)
        status_frame.pack(side='bottom', fill='x', padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready - Synchronized scrolling enabled", relief='sunken')
        self.status_label.pack(side='left', fill='x', expand=True)
        
        self.progress_bar = ttk.Progressbar(status_frame, mode='determinate', length=200)
        self.progress_bar.pack(side='right', padx=5)
        
        # Main panes
        main_paned = ttk.PanedWindow(self, orient='vertical')
        main_paned.pack(expand=True, fill='both', padx=5, pady=5)
        
        # === PANE 1: Tree ===
        tree_frame = ttk.LabelFrame(main_paned, text="Changes Summary", padding=5)
        main_paned.add(tree_frame, weight=2)
        
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(expand=True, fill='both')
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('num', 'config', 'type', 'path', 'old', 'new'),
            show='tree headings',
            selectmode='browse',
            height=12
        )
        
        self.tree.heading('#0', text='')
        self.tree.heading('num', text='#')
        self.tree.heading('config', text='Config Key')
        self.tree.heading('type', text='Type')
        self.tree.heading('path', text='JSON Path')
        self.tree.heading('old', text='Old Value')
        self.tree.heading('new', text='New Value')
        
        self.tree.column('#0', width=0, stretch=False)
        self.tree.column('num', width=50, anchor='center')
        self.tree.column('config', width=180)
        self.tree.column('type', width=90, anchor='center')
        self.tree.column('path', width=350)
        self.tree.column('old', width=300)
        self.tree.column('new', width=300)
        
        self.tree.tag_configure('changed', background=CONFIG.COLOR_CHANGED_BG)
        self.tree.tag_configure('added', background=CONFIG.COLOR_ADDED_BG)
        self.tree.tag_configure('removed', background=CONFIG.COLOR_REMOVED_BG)
        
        vsb = ttk.Scrollbar(tree_container, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Pagination
        nav_frame = ttk.Frame(tree_frame)
        nav_frame.pack(fill='x', pady=5)
        
        ttk.Button(nav_frame, text="◀◀", command=self.first_page, width=8).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="◀", command=self.prev_page, width=8).pack(side='left', padx=2)
        
        self.page_label = ttk.Label(nav_frame, text="Page 0/0", font=self.bold_font)
        self.page_label.pack(side='left', padx=15)
        
        ttk.Button(nav_frame, text="▶", command=self.next_page, width=8).pack(side='left', padx=2)
        ttk.Button(nav_frame, text="▶▶", command=self.last_page, width=8).pack(side='left', padx=2)
        
        # === PANE 2: Inline Diff ===
        inline_frame = ttk.LabelFrame(main_paned, text="Selected Item - Character Diff", padding=5)
        main_paned.add(inline_frame, weight=1)
        
        inline_paned = ttk.PanedWindow(inline_frame, orient='horizontal')
        inline_paned.pack(expand=True, fill='both')
        
        # Old
        old_inline = ttk.Frame(inline_paned)
        inline_paned.add(old_inline, weight=1)
        ttk.Label(old_inline, text="Old Value", font=self.bold_font, foreground='#C62828').pack()
        
        self.txt_inline_old = tk.Text(old_inline, height=8, wrap='word', font=self.mono_font)
        old_inline_scroll = ttk.Scrollbar(old_inline, command=self.txt_inline_old.yview)
        self.txt_inline_old.configure(yscrollcommand=old_inline_scroll.set)
        self.txt_inline_old.pack(side='left', expand=True, fill='both')
        old_inline_scroll.pack(side='right', fill='y')
        
        self.txt_inline_old.tag_configure('equal', background=CONFIG.COLOR_EQUAL)
        self.txt_inline_old.tag_configure('delete', background=CONFIG.COLOR_DIFF_OLD, foreground='black')
        
        # New
        new_inline = ttk.Frame(inline_paned)
        inline_paned.add(new_inline, weight=1)
        ttk.Label(new_inline, text="New Value", font=self.bold_font, foreground='#2E7D32').pack()
        
        self.txt_inline_new = tk.Text(new_inline, height=8, wrap='word', font=self.mono_font)
        new_inline_scroll = ttk.Scrollbar(new_inline, command=self.txt_inline_new.yview)
        self.txt_inline_new.configure(yscrollcommand=new_inline_scroll.set)
        self.txt_inline_new.pack(side='left', expand=True, fill='both')
        new_inline_scroll.pack(side='right', fill='y')
        
        self.txt_inline_new.tag_configure('equal', background=CONFIG.COLOR_EQUAL)
        self.txt_inline_new.tag_configure('insert', background=CONFIG.COLOR_DIFF_NEW, foreground='black')
        
        # === PANE 3: Full Payloads with SYNCHRONIZED SCROLLING ===
        payload_frame = ttk.LabelFrame(main_paned, text="Full Payloads - SYNCHRONIZED (Blue Highlights)", padding=5)
        main_paned.add(payload_frame, weight=3)
        
        payload_paned = ttk.PanedWindow(payload_frame, orient='horizontal')
        payload_paned.pack(expand=True, fill='both')
        
        # OLD Payload
        old_payload = ttk.Frame(payload_paned)
        payload_paned.add(old_payload, weight=1)
        ttk.Label(old_payload, text="OLD Payload", font=self.bold_font, foreground='#C62828').pack()
        
        old_payload_container = ttk.Frame(old_payload)
        old_payload_container.pack(expand=True, fill='both')
        
        self.txt_old = tk.Text(old_payload_container, wrap='none', font=self.mono_font)
        self.old_scroll_y = ttk.Scrollbar(old_payload_container, orient='vertical', command=self._on_old_scroll)
        self.old_scroll_x = ttk.Scrollbar(old_payload_container, orient='horizontal', command=self.txt_old.xview)
        self.txt_old.configure(yscrollcommand=self._update_old_scrollbar, xscrollcommand=self.old_scroll_x.set)
        
        self.txt_old.grid(row=0, column=0, sticky='nsew')
        self.old_scroll_y.grid(row=0, column=1, sticky='ns')
        self.old_scroll_x.grid(row=1, column=0, sticky='ew')
        
        old_payload_container.grid_rowconfigure(0, weight=1)
        old_payload_container.grid_columnconfigure(0, weight=1)
        
        self.txt_old.tag_configure('highlight', background=CONFIG.COLOR_HIGHLIGHT_LINE, foreground='black')
        
        # CURRENT Payload
        new_payload = ttk.Frame(payload_paned)
        payload_paned.add(new_payload, weight=1)
        ttk.Label(new_payload, text="CURRENT Payload", font=self.bold_font, foreground='#2E7D32').pack()
        
        new_payload_container = ttk.Frame(new_payload)
        new_payload_container.pack(expand=True, fill='both')
        
        self.txt_new = tk.Text(new_payload_container, wrap='none', font=self.mono_font)
        self.new_scroll_y = ttk.Scrollbar(new_payload_container, orient='vertical', command=self._on_new_scroll)
        self.new_scroll_x = ttk.Scrollbar(new_payload_container, orient='horizontal', command=self.txt_new.xview)
        self.txt_new.configure(yscrollcommand=self._update_new_scrollbar, xscrollcommand=self.new_scroll_x.set)
        
        self.txt_new.grid(row=0, column=0, sticky='nsew')
        self.new_scroll_y.grid(row=0, column=1, sticky='ns')
        self.new_scroll_x.grid(row=1, column=0, sticky='ew')
        
        new_payload_container.grid_rowconfigure(0, weight=1)
        new_payload_container.grid_columnconfigure(0, weight=1)
        
        self.txt_new.tag_configure('highlight', background=CONFIG.COLOR_HIGHLIGHT_LINE, foreground='black')
        
        # SYNCHRONIZED SCROLLING: Bind mousewheel to both
        self.txt_old.bind('<MouseWheel>', self._on_mousewheel_old)
        self.txt_new.bind('<MouseWheel>', self._on_mousewheel_new)
        self.txt_old.bind('<Button-4>', self._on_mousewheel_old)  # Linux
        self.txt_old.bind('<Button-5>', self._on_mousewheel_old)
        self.txt_new.bind('<Button-4>', self._on_mousewheel_new)
        self.txt_new.bind('<Button-5>', self._on_mousewheel_new)
        
        # Bind selection
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    # === SYNCHRONIZED SCROLLING METHODS ===
    def _on_old_scroll(self, *args):
        """When OLD scrollbar moves, sync NEW."""
        self.txt_old.yview(*args)
        self.txt_new.yview(*args)
    
    def _on_new_scroll(self, *args):
        """When NEW scrollbar moves, sync OLD."""
        self.txt_new.yview(*args)
        self.txt_old.yview(*args)
    
    def _update_old_scrollbar(self, first, last):
        """Update OLD scrollbar and sync NEW."""
        self.old_scroll_y.set(first, last)
        # Keep NEW in sync
        if self.txt_new.yview() != (float(first), float(last)):
            self.txt_new.yview_moveto(first)
    
    def _update_new_scrollbar(self, first, last):
        """Update NEW scrollbar and sync OLD."""
        self.new_scroll_y.set(first, last)
        # Keep OLD in sync
        if self.txt_old.yview() != (float(first), float(last)):
            self.txt_old.yview_moveto(first)
    
    def _on_mousewheel_old(self, event):
        """Mousewheel on OLD - sync NEW."""
        delta = -1 if event.delta < 0 or event.num == 5 else 1
        self.txt_old.yview_scroll(delta, "units")
        self.txt_new.yview_scroll(delta, "units")
        return "break"
    
    def _on_mousewheel_new(self, event):
        """Mousewheel on NEW - sync OLD."""
        delta = -1 if event.delta < 0 or event.num == 5 else 1
        self.txt_new.yview_scroll(delta, "units")
        self.txt_old.yview_scroll(delta, "units")
        return "break"
    
    # === FILE LOADING ===
    def load_file(self, file_path: str = None):
        """Load file."""
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="Select Payload File",
                filetypes=[
                    ("All Supported", "*.csv *.xlsx *.xls *.xlsb"),
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx *.xls *.xlsb"),
                    ("All files", "*.*")
                ]
            )
        
        if not file_path:
            return
        
        file_path = file_path.strip('{}')
        
        if not Path(file_path).exists():
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
        
        self.status_label.config(text=f"Loading {Path(file_path).name}...")
        self.progress_bar['value'] = 0
        self.update_idletasks()
        
        thread = threading.Thread(target=self._load_worker, args=(file_path,), daemon=True)
        thread.start()
    
    def _load_worker(self, file_path: str):
        """Load worker."""
        try:
            start = pd.Timestamp.now()
            
            def progress(curr, total):
                pct = (curr / total * 100) if total > 0 else 0
                self.after(0, lambda: self._update_progress(pct, f"Loading: {curr:,}/{total:,}"))
            
            self.df = self.loader.load_full_optimized(file_path, progress_callback=progress)
            self._process_data()
            
            elapsed = (pd.Timestamp.now() - start).total_seconds()
            rps = len(self.df) / elapsed if elapsed > 0 else 0
            
            self.after(0, lambda: self._on_load_done(file_path, elapsed, rps))
            
        except Exception as e:
            logger.error(f"Load failed: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
    
    def _process_data(self):
        """Process data."""
        if self.df is None or self.df.empty:
            raise ValueError("No data")
        
        mappings = {
            'config_name': ['config', 'config_name', 'name'],
            'payload_json': ['payload', 'payload_json', 'current'],
            'prev_payload_json': ['prev', 'previous', 'prev_payload', 'old'],
            'timestamp': ['timestamp', 'time', 'updated']
        }
        
        for target, candidates in mappings.items():
            if target not in self.df.columns:
                for candidate in candidates:
                    matches = [c for c in self.df.columns if candidate in c.lower()]
                    if matches:
                        self.df = self.df.rename(columns={matches[0]: target})
                        break
        
        if 'config_name' in self.df.columns:
            self.df['config_name'] = self.df['config_name'].astype(str).str.strip()
        
        if len(self.df) > CONFIG.max_records:
            self.df = self.df.head(CONFIG.max_records)
        
        self.filtered_df = None
        self.filter_active = False
    
    def _on_load_done(self, path, elapsed, rps):
        """On load complete."""
        self.progress_bar['value'] = 100
        self.status_label.config(text=f"✓ {len(self.df):,} rows in {elapsed:.2f}s ({rps:,.0f} rows/s)")
        
        self.total_pages = max(1, (len(self.df) + CONFIG.page_size - 1) // CONFIG.page_size)
        self.current_page = 0
        
        self._compute_diffs_for_page()
        
        messagebox.showinfo("Success", f"Loaded {len(self.df):,} rows in {elapsed:.2f}s")
    
    def _update_progress(self, pct, msg):
        """Update progress."""
        self.progress_bar['value'] = pct
        self.status_label.config(text=msg)
        self.update_idletasks()
    
    def _compute_diffs_for_page(self):
        """Compute diffs."""
        if self.df is None:
            return
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_meta.clear()
        self.full_payloads_cache.clear()
        self.config_diffs.clear()
        
        df_display = self.filtered_df if self.filter_active else self.df
        start_idx = self.current_page * CONFIG.page_size
        end_idx = min(start_idx + CONFIG.page_size, len(df_display))
        page_data = df_display.iloc[start_idx:end_idx]
        
        row_num = 0
        
        for idx, row in page_data.iterrows():
            config = row.get('config_name', 'N/A')
            
            try:
                prev_json = row.get('prev_payload_json', '{}')
                curr_json = row.get('payload_json', '{}')
                
                prev_obj = json.loads(prev_json) if pd.notna(prev_json) and prev_json else {}
                curr_obj = json.loads(curr_json) if pd.notna(curr_json) and curr_json else {}
                
                self.full_payloads_cache[config] = (prev_obj, curr_obj)
                
                dd = DeepDiff(prev_obj, curr_obj, ignore_order=True, verbose_level=2)
                
                diff_list = []
                
                # Values changed
                for path, change in dd.get('values_changed', {}).items():
                    diff_list.append(RowMeta(
                        cfgkey=config,
                        typ='changed',
                        path=dd_path_to_key(path),
                        old=change.get('old_value'),
                        new=change.get('new_value')
                    ))
                
                # Type changes
                for path, change in dd.get('type_changes', {}).items():
                    diff_list.append(RowMeta(
                        cfgkey=config,
                        typ='changed',
                        path=dd_path_to_key(path),
                        old=change.get('old_value'),
                        new=change.get('new_value')
                    ))
                
                # Added
                for path in dd.get('dictionary_item_added', set()):
                    val = value_from_path(curr_obj, path)
                    diff_list.append(RowMeta(
                        cfgkey=config,
                        typ='added',
                        path=dd_path_to_key(path),
                        old=None,
                        new=val
                    ))
                
                # Removed
                for path in dd.get('dictionary_item_removed', set()):
                    val = value_from_path(prev_obj, path)
                    diff_list.append(RowMeta(
                        cfgkey=config,
                        typ='removed',
                        path=dd_path_to_key(path),
                        old=val,
                        new=None
                    ))
                
                # Store all diffs for this config
                self.config_diffs[config] = diff_list
                
                # Populate tree
                for meta in diff_list:
                    row_num += 1
                    iid = self.tree.insert('', 'end',
                                          values=(
                                              row_num,
                                              meta.cfgkey,
                                              meta.typ.upper(),
                                              meta.path,
                                              self._fmt_val(meta.old),
                                              self._fmt_val(meta.new)
                                          ),
                                          tags=(meta.typ,))
                    self.tree_meta[iid] = meta
                
            except Exception as e:
                logger.error(f"Diff failed for {config}: {e}")
        
        self.page_label.config(text=f"Page {self.current_page+1}/{self.total_pages} ({len(df_display):,} rows)")
    
    def _fmt_val(self, val: Any) -> str:
        """Format value."""
        if val is None:
            return ""
        try:
            s = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)
            return s if len(s) <= 100 else s[:97] + "..."
        except:
            return str(val)[:100]
    
    def on_tree_select(self, event):
        """Handle selection - show ALL changes for config with BLUE highlights."""
        selection = self.tree.selection()
        if not selection:
            return
        
        iid = selection[0]
        meta = self.tree_meta.get(iid)
        if not meta:
            return
        
        # === PANE 2: Inline diff ===
        old_str = self._fmt_val(meta.old)
        new_str = self._fmt_val(meta.new)
        
        self.txt_inline_old.delete(1.0, tk.END)
        self.txt_inline_new.delete(1.0, tk.END)
        
        sm = difflib.SequenceMatcher(a=old_str, b=new_str)
        
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal':
                self.txt_inline_old.insert(tk.END, old_str[i1:i2], 'equal')
                self.txt_inline_new.insert(tk.END, new_str[j1:j2], 'equal')
            elif op == 'delete':
                self.txt_inline_old.insert(tk.END, old_str[i1:i2], 'delete')
            elif op == 'insert':
                self.txt_inline_new.insert(tk.END, new_str[j1:j2], 'insert')
            elif op == 'replace':
                self.txt_inline_old.insert(tk.END, old_str[i1:i2], 'delete')
                self.txt_inline_new.insert(tk.END, new_str[j1:j2], 'insert')
        
        # === PANE 3: Full payloads with ALL changes highlighted in BLUE ===
        if meta.cfgkey in self.full_payloads_cache:
            old_obj, new_obj = self.full_payloads_cache[meta.cfgkey]
            
            self.txt_old.delete(1.0, tk.END)
            self.txt_new.delete(1.0, tk.END)
            
            old_json = pretty_json(old_obj)
            new_json = pretty_json(new_obj)
            
            self.txt_old.insert(1.0, old_json)
            self.txt_new.insert(1.0, new_json)
            
            # Highlight ALL changes for this config (not just selected one)
            all_diffs = self.config_diffs.get(meta.cfgkey, [])
            for diff_meta in all_diffs:
                leaf_key = diff_meta.path.split('.')[-1].split('[')[0] if diff_meta.path else ""
                self._highlight_all_lines(self.txt_old, leaf_key, diff_meta.old)
                self._highlight_all_lines(self.txt_new, leaf_key, diff_meta.new)
    
    def _highlight_all_lines(self, widget: tk.Text, key: str, value: Any):
        """Highlight ALL lines matching key/value in BLUE."""
        text = widget.get(1.0, 'end-1c')
        if not text.strip() or not key:
            return
        
        try:
            value_str = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, str)) else str(value)
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                # Highlight if line contains the key
                if key in line:
                    line_start = f"{i+1}.0"
                    line_end = f"{i+1}.end"
                    widget.tag_add('highlight', line_start, line_end)
        except:
            pass
    
    def refresh_page(self):
        self._compute_diffs_for_page()
    
    def first_page(self):
        if self.current_page != 0:
            self.current_page = 0
            self.refresh_page()
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_page()
    
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.refresh_page()
    
    def last_page(self):
        if self.current_page != self.total_pages - 1:
            self.current_page = self.total_pages - 1
            self.refresh_page()
    
    def show_filter(self):
        if self.df is None:
            return
        text = simpledialog.askstring("Filter", "Enter config name:")
        if text:
            self.filtered_df = self.df[self.df['config_name'].str.contains(text, case=False, na=False)]
            self.filter_active = True
            self.total_pages = max(1, (len(self.filtered_df) + CONFIG.page_size - 1) // CONFIG.page_size)
            self.current_page = 0
            self.refresh_page()
    
    def export_csv(self):
        if self.df is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            self.df.to_csv(path, index=False)
            messagebox.showinfo("Success", f"Exported to {path}")
    
    def show_stats(self):
        if self.df is None:
            return
        stats = f"""Statistics

Total Rows: {len(self.df):,}
Columns: {len(self.df.columns)}
Memory: {self.df.memory_usage(deep=True).sum() / (1024**2):.2f} MB

Columns:
{chr(10).join('  • ' + col for col in self.df.columns)}
"""
        messagebox.showinfo("Statistics", stats)


if __name__ == "__main__":
    try:
        app = PerfectDiffViewer()
        app.mainloop()
    except Exception as e:
        print(f"ERROR: {e}")
        logger.error(f"Failed: {e}", exc_info=True)
        input("Press Enter to exit...")
