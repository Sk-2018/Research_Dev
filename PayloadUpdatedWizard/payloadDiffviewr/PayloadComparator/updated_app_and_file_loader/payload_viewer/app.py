import os
import re
import sys
import threading
import queue
import time
from typing import Any, Optional, List, Dict, Tuple
import tkinter as tk
from tkinter import (
    ttk, 
    filedialog, 
    messagebox, 
    simpledialog, 
    scrolledtext, 
    Menu
)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    
from . import ui_config
from .settings import SettingsManager
from .sharepoint import sharepoint_url_to_unc
from .parse_logger import ParseLogger
from .file_loader import FileLoader
from .json_utils import try_parse_json, json_to_pretty_text, find_line_index
from .diff_engine import run_deepdiff
from .summary_dashboard import SummaryDashboard


class PayloadDiffViewerApp:
    """
    Main application class for the Payload Diff Viewer.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Payload Diff Viewer")
        self.root.geometry(ui_config.DEFAULT_APP_GEOMETRY)
        
        # Fix for Windows high-DPI scaling
        if sys.platform == "win32":
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass # Ignore if it fails
                
        # Optional: Set a modern theme if azure.tcl is available
        # self.root.tk.call('source', 'azure.tcl')
        # self.root.tk.call("set_theme", "light")

        # --- Core Components ---
        self.settings = SettingsManager()
        self.parse_logger = ParseLogger(self.root)
        self.file_loader = FileLoader(self.parse_logger)
        self.summary_window: Optional[SummaryDashboard] = None
        
        # --- Data State ---
        self.full_data_df: Optional["pd.DataFrame"] = None
        self.headers: List[str] = []
        self.raw_rows: List[List[Any]] = []
        self.current_diff_results: dict = {}
        self.diff_data_map: Dict[str, dict] = {} # Maps tree item ID to diff data
        
        # --- UI State ---
        self.column_vars: Dict[str, tk.StringVar] = {
            "config_name": tk.StringVar(),
            "config_key": tk.StringVar(),
            "old_payload": tk.StringVar(),
            "new_payload": tk.StringVar(),
        }
        self.ignore_order_var = tk.BooleanVar(value=False)
        self.coerce_numeric_var = tk.BooleanVar(value=True)
        self.watch_list_var = tk.StringVar()
        self.watch_only_var = tk.BooleanVar(value=False)
        self.filter_var = tk.StringVar()
        self._scroll_syncing = False # Re-entrant guard for scroll sync

        # --- Build UI ---
        self._create_menus()
        self._create_main_layout()
        self._create_toolbar()
        self._create_diff_table()
        self._create_inline_diff_panes()
        self._create_full_json_panes()
        self._create_statusbar()
        
        # --- Bindings ---
        self._bind_events()
        
        self.parse_logger.info("Application started.")

    # --- UI Creation Methods ---

    def _create_menus(self):
        """Creates the main application menu bar."""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # --- File Menu ---
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Open...", 
            command=self.open_file,
            accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Set Default Folder...", 
            command=self.set_default_folder
        )
        file_menu.add_command(
            label="Set Default from SharePoint URL...",
            command=self.set_default_sharepoint
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Export Diff Table...",
            command=self.export_diff_table
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # --- View Menu ---
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="Summary Dashboard",
            command=self.show_summary,
            accelerator="Ctrl+M"
        )
        view_menu.add_checkbutton(
            label="Coerce Numeric Types",
            variable=self.coerce_numeric_var,
            onvalue=True, offvalue=False
        )
        
        # --- Help Menu ---
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Show Parse Log", command=self.parse_logger.show)
        help_menu.add_command(label="About", command=self.show_about)

    def _create_main_layout(self):
        """Creates the main PanedWindow layout."""
        # Top-to-bottom layout: Toolbar, Main, Status
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.toolbar_frame = ttk.Frame(self.root, padding=(5, 5))
        self.toolbar_frame.grid(row=0, column=0, sticky="ew")

        # Main content area: vertical panes
        self.main_v_pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.main_v_pane.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))

        # Top half: Diff Table
        self.table_frame = ttk.Frame(self.main_v_pane, relief=tk.GROOVE, borderwidth=1)
        self.table_frame.grid_rowconfigure(1, weight=1) # Note: row 1 for treeview
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.main_v_pane.add(self.table_frame, weight=2) # Diff table gets more space

        # Bottom half: Panes (Inline + Full)
        self.bottom_frame = ttk.Frame(self.main_v_pane)
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.main_v_pane.add(self.bottom_frame, weight=3) # JSON viewers get more
        
        # Bottom frame horizontal pane (Inline | Full)
        self.bottom_h_pane = ttk.PanedWindow(self.bottom_frame, orient=tk.HORIZONTAL)
        self.bottom_h_pane.grid(row=0, column=0, sticky="nsew")

        self.inline_frame = ttk.Frame(self.bottom_h_pane, relief=tk.GROOVE, borderwidth=1)
        self.bottom_h_pane.add(self.inline_frame, weight=1)
        
        self.full_json_frame = ttk.Frame(self.bottom_h_pane, relief=tk.GROOVE, borderwidth=1)
        self.bottom_h_pane.add(self.full_json_frame, weight=3)

        # Status Bar
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(2, 2))
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def _create_toolbar(self):
        """Creates the toolbar for file loading and comparison."""
        frame = self.toolbar_frame
        
        ttk.Button(frame, text="Open File (Ctrl+O)", command=self.open_file).pack(side=tk.LEFT, padx=2)
        
        # Column selectors
        ttk.Label(frame, text="Config Name:").pack(side=tk.LEFT, padx=(10, 2))
        self.name_combo = ttk.Combobox(
            frame, 
            textvariable=self.column_vars["config_name"], 
            width=15
        )
        self.name_combo.pack(side=tk.LEFT, padx=2)

        ttk.Label(frame, text="Config Key:").pack(side=tk.LEFT, padx=(10, 2))
        self.key_combo = ttk.Combobox(
            frame, 
            textvariable=self.column_vars["config_key"], 
            width=15
        )
        self.key_combo.pack(side=tk.LEFT, padx=2)

        ttk.Label(frame, text="Old Payload:").pack(side=tk.LEFT, padx=(10, 2))
        self.old_combo = ttk.Combobox(
            frame, 
            textvariable=self.column_vars["old_payload"], 
            width=20
        )
        self.old_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(frame, text="New Payload:").pack(side=tk.LEFT, padx=(10, 2))
        self.new_combo = ttk.Combobox(
            frame, 
            textvariable=self.column_vars["new_payload"], 
            width=20
        )
        self.new_combo.pack(side=tk.LEFT, padx=2)

        ttk.Button(frame, text="Compare (F5)", command=self.run_compare).pack(side=tk.LEFT, padx=(10, 2))
        
        self.compare_progress = ttk.Progressbar(
            frame, 
            orient=tk.HORIZONTAL, 
            length=100, 
            mode='indeterminate'
        )
        # self.compare_progress.pack(side=tk.LEFT, padx=5, pady=5) # Hide initially

    def _create_diff_table(self):
        """Creates the main diff Treeview and its controls."""
        frame = self.table_frame
        
        # --- Filter bar ---
        filter_frame = ttk.Frame(frame, padding=(5, 5))
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        ttk.Label(filter_frame, text="Filter (Ctrl+F):").pack(side=tk.LEFT)
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=30)
        self.filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ttk.Label(filter_frame, text="Watchlist (keys,):").pack(side=tk.LEFT, padx=(10, 2))
        self.watch_entry = ttk.Entry(filter_frame, textvariable=self.watch_list_var, width=30)
        self.watch_entry.pack(side=tk.LEFT, padx=5)
        self.watch_only_check = ttk.Checkbutton(
            filter_frame,
            text="Only Watch",
            variable=self.watch_only_var
        )
        self.watch_only_check.pack(side=tk.LEFT)

        self.array_toggle = ttk.Checkbutton(
            filter_frame,
            text="Arrays as Set (Ignore Order)",
            variable=self.ignore_order_var
        )
        self.array_toggle.pack(side=tk.LEFT, padx=(10, 0))
        
        # --- Treeview ---
        cols = list(ui_config.DIFF_TABLE_COLUMNS.keys())
        self.diff_tree = ttk.Treeview(
            frame, 
            columns=cols, 
            show="headings",
            selectmode="browse"
        )
        self.diff_tree.grid(row=1, column=0, sticky="nsew")
        
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.diff_tree.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.diff_tree.xview)
        hsb.grid(row=2, column=0, sticky="ew")
        
        self.diff_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        for col_name, width in ui_config.DIFF_TABLE_COLUMNS.items():
            self.diff_tree.heading(col_name, text=col_name)
            self.diff_tree.column(col_name, width=width, stretch=True)

        # Configure row color tags
        self.diff_tree.tag_configure(
            "changed", 
            background=ui_config.COLOR_TAG_CHANGED[0],
            foreground=ui_config.COLOR_TAG_CHANGED[1]
        )
        self.diff_tree.tag_configure(
            "added", 
            background=ui_config.COLOR_TAG_ADDED[0],
            foreground=ui_config.COLOR_TAG_ADDED[1]
        )
        self.diff_tree.tag_configure(
            "removed",
            background=ui_config.COLOR_TAG_REMOVED[0],
            foreground=ui_config.COLOR_TAG_REMOVED[1]
        )
        self.diff_tree.tag_configure(
            "watch",
            background=ui_config.COLOR_TAG_WATCH[0],
            foreground=ui_config.COLOR_TAG_WATCH[1],
            font=ui_config.FONT_BOLD
        )

    def _create_inline_diff_panes(self):
        """Creates the 'Old' and 'New' inline text boxes."""
        frame = self.inline_frame
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(frame, text="Old Value (Inline)", font=ui_config.FONT_BOLD).grid(
            row=0, column=0, sticky="w", padx=5, pady=(5,0)
        )
        self.inline_old_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            font=ui_config.FONT_CODE,
            height=10,
            bg=ui_config.COLOR_BG_TEXT_READONLY,
            state="disabled"
        )
        self.inline_old_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=2)
        
        ttk.Label(frame, text="New Value (Inline)", font=ui_config.FONT_BOLD).grid(
            row=2, column=0, sticky="w", padx=5, pady=(5,0)
        )
        self.inline_new_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            font=ui_config.FONT_CODE,
            height=10,
            bg=ui_config.COLOR_BG_TEXT_READONLY,
            state="disabled"
        )
        self.inline_new_text.grid(row=3, column=0, sticky="nsew", padx=5, pady=(2, 5))

    def _create_full_json_panes(self):
        """Creates the two large, synchronized full JSON text panes."""
        frame = self.full_json_frame
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        
        # --- Left/Old Pane ---
        ttk.Label(frame, text="Full OLD Payload", font=ui_config.FONT_BOLD).grid(
            row=0, column=0, sticky="w", padx=5, pady=(5,0)
        )
        self.text_old_frame = ttk.Frame(frame)
        self.text_old_frame.grid(row=1, column=0, sticky="nsew", padx=(5, 0))
        self.text_old_frame.grid_rowconfigure(0, weight=1)
        self.text_old_frame.grid_columnconfigure(0, weight=1)
        
        self.vsb_old = ttk.Scrollbar(self.text_old_frame, orient=tk.VERTICAL)
        self.vsb_old.grid(row=0, column=1, sticky="ns")
        self.text_old = tk.Text(
            self.text_old_frame,
            wrap=tk.WORD,
            font=ui_config.FONT_CODE,
            bg=ui_config.COLOR_BG_TEXT_READONLY,
            state="disabled",
            yscrollcommand=self.vsb_old.set # Will be re-wired
        )
        self.text_old.grid(row=0, column=0, sticky="nsew")

        # --- Right/New Pane ---
        ttk.Label(frame, text="Full NEW Payload", font=ui_config.FONT_BOLD).grid(
            row=0, column=2, sticky="w", padx=5, pady=(5,0)
        )
        self.text_new_frame = ttk.Frame(frame)
        self.text_new_frame.grid(row=1, column=2, sticky="nsew", padx=(5, 5))
        self.text_new_frame.grid_rowconfigure(0, weight=1)
        self.text_new_frame.grid_columnconfigure(0, weight=1)
        
        self.vsb_new = ttk.Scrollbar(self.text_new_frame, orient=tk.VERTICAL)
        self.vsb_new.grid(row=0, column=1, sticky="ns")
        self.text_new = tk.Text(
            self.text_new_frame,
            wrap=tk.WORD,
            font=ui_config.FONT_CODE,
            bg=ui_config.COLOR_BG_TEXT_READONLY,
            state="disabled",
            yscrollcommand=self.vsb_new.set # Will be re-wired
        )
        self.text_new.grid(row=0, column=0, sticky="nsew")

        # --- Synchronized Scrollbar (Middle) ---
        # We can use one of the existing scrollbars (e.g., vsb_old)
        # and hide the other, or link them.
        # Per prompt: "wire scrollbars explicitly" and "No recursion"
        # We will use *both* scrollbars but make them control *both* panes.
        
        self.vsb_old.config(command=self._sync_yview)
        self.vsb_new.config(command=self._sync_yview)
        
        self.text_old.config(yscrollcommand=self._on_text_scroll_old)
        self.text_new.config(yscrollcommand=self._on_text_scroll_new)
        
        # Configure highlight tag
        self.text_old.tag_configure(
            'hit', 
            background=ui_config.COLOR_HIGHLIGHT_BG, 
            foreground=ui_config.COLOR_HIGHLIGHT_FG
        )
        self.text_new.tag_configure(
            'hit', 
            background=ui_config.COLOR_HIGHLIGHT_BG, 
            foreground=ui_config.COLOR_HIGHLIGHT_FG
        )

    def _create_statusbar(self):
        """Creates the bottom status bar."""
        self.status_var = tk.StringVar(value="Ready.")
        status_label = ttk.Label(
            self.status_bar, 
            textvariable=self.status_var, 
            anchor=tk.W
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.row_count_var = tk.StringVar(value="Rows: 0")
        row_label = ttk.Label(self.status_bar, textvariable=self.row_count_var)
        row_label.pack(side=tk.RIGHT, padx=5)

    def _bind_events(self):
        """Binds all keyboard and UI events."""
        # --- Menu/Global Shortcuts ---
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-m>", lambda e: self.show_summary())
        self.root.bind("<F5>", lambda e: self.run_compare())
        self.root.bind("<Control-f>", lambda e: self.filter_entry.focus_set())
        
        # --- UI Callbacks ---
        self.filter_var.trace_add("write", self._schedule_filter_update)
        self.watch_list_var.trace_add("write", self._schedule_filter_update)
        self.watch_only_var.trace_add("write", self._schedule_filter_update)
        self.ignore_order_var.trace_add("write", self._schedule_filter_update)
        
        self.diff_tree.bind("<<TreeviewSelect>>", self.on_diff_row_selected)
        
        # --- Synchronized Scrolling Events ---
        # Mouse wheel bindings
        self.text_old.bind("<MouseWheel>", self._on_mousewheel)
        self.text_new.bind("<MouseWheel>", self._on_mousewheel)
        # Linux mouse wheel
        self.text_old.bind("<Button-4>", self._on_mousewheel) 
        self.text_old.bind("<Button-5>", self._on_mousewheel)
        self.text_new.bind("<Button-4>", self._on_mousewheel)
        self.text_new.bind("<Button-5>", self._on_mousewheel)
        
        # Debounce timer for filtering
        self._filter_job = None
        
    # --- Synchronized Scrolling Callbacks ---

    def _sync_yview(self, *args):
        """
        Called by scrollbar *commands*. Scrolls both text widgets.
        Uses a re-entrant guard.
        """
        if self._scroll_syncing:
            return
        self._scroll_syncing = True
        try:
            self.text_old.yview(*args)
            self.text_new.yview(*args)
        finally:
            self._scroll_syncing = False

    def _on_text_scroll_old(self, *args):
        """
        Called by text_old's *yscrollcommand*.
        Updates both scrollbars and scrolls the *other* text widget.
        """
        if self._scroll_syncing:
            return
        self._scroll_syncing = True
        try:
            # Update both scrollbars to match the one that moved
            self.vsb_old.set(*args)
            self.vsb_new.set(*args)
            # Sync the other text widget
            self.text_new.yview_moveto(args[0])
        finally:
            self._scroll_syncing = False

    def _on_text_scroll_new(self, *args):
        """
        Called by text_new's *yscrollcommand*.
        Symmetrical to _on_text_scroll_old.
        """
        if self._scroll_syncing:
            return
        self._scroll_syncing = True
        try:
            # Update both scrollbars
            self.vsb_old.set(*args)
            self.vsb_new.set(*args)
            # Sync the other text widget
            self.text_old.yview_moveto(args[0])
        finally:
            self._scroll_syncing = False
            
    def _on_mousewheel(self, event):
        """Handles mouse wheel scrolling for both panes."""
        if self._scroll_syncing:
            return
        self._scroll_syncing = True
        try:
            # Determine scroll direction (Windows vs Linux)
            if event.num == 4: # Linux scroll up
                delta = -1
            elif event.num == 5: # Linux scroll down
                delta = 1
            else: # Windows
                delta = -1 * (event.delta // 120)
                
            self.text_old.yview_scroll(delta, "units")
            self.text_new.yview_scroll(delta, "units")
            
            # Update scrollbars from one of the text widgets
            # We call one of the text scroll handlers directly
            self._on_text_scroll_old(*self.text_old.yview())
            
        finally:
            self._scroll_syncing = False
        
        return "break" # Prevent default scroll behavior
        
    # --- Core Application Logic ---

    def _update_comboboxes(self):
        """Updates combobox choices after loading a file."""
        col_list = self.headers
        combos = [self.name_combo, self.key_combo, self.old_combo, self.new_combo]
        for combo in combos:
            combo['values'] = col_list
            
        # Try to auto-detect best columns
        if not PANDAS_AVAILABLE or self.full_data_df is None:
            self.parse_logger.warn("pandas not available, skipping column detection.")
            return
            
        try:
            best_cols = self.file_loader.detect_best_columns(self.full_data_df)
            
            if best_cols.get("config_name_col"):
                self.column_vars["config_name"].set(best_cols["config_name_col"])
            if best_cols.get("config_key_col"):
                self.column_vars["config_key"].set(best_cols["config_key_col"])
            if best_cols.get("old_payload_col"):
                self.column_vars["old_payload"].set(best_cols["old_payload_col"])
            if best_cols.get("new_payload_col"):
                self.column_vars["new_payload"].set(best_cols["new_payload_col"])
                
        except Exception as e:
            self.parse_logger.error(f"Error auto-detecting columns: {e}")

    def _show_loading_progress(self, title: str) -> Tuple[tk.Toplevel, ttk.Progressbar, tk.StringVar]:
        """Displays a modal progress dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        frame = ttk.Frame(dialog, padding=20)
        frame.pack()
        
        status_var = tk.StringVar(value="Initializing...")
        ttk.Label(frame, textvariable=status_var, width=50).pack(pady=5)
        
        progress_bar = ttk.Progressbar(
            frame, 
            orient=tk.HORIZONTAL, 
            length=300, 
            mode='determinate'
        )
        progress_bar.pack(pady=10)
        
        self.root.update_idletasks()
        # Center dialog
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        return dialog, progress_bar, status_var

    def open_file(self):
        """Shows file dialog and loads selected file in a thread."""
        default_dir = self.settings.get("default_open_dir", os.path.expanduser("~"))
        
        # Check if it's a SharePoint path and resolve it
        if default_dir.startswith("http"):
            self.status_var.set("Resolving SharePoint URL...")
            self.root.update_idletasks()
            unc_path = sharepoint_url_to_unc(default_dir)
            if unc_path:
                default_dir = unc_path
                self.parse_logger.info(f"Resolved SharePoint URL to {unc_path}")
            else:
                self.parse_logger.warn(f"Could not resolve SharePoint URL: {default_dir}")
                default_dir = os.path.expanduser("~") # Fallback
            self.status_var.set("Ready.")
                
        filepath = filedialog.askopenfilename(
            title="Open Payload File",
            initialdir=default_dir,
            filetypes=[
                ("Supported Files", "*.csv *.tsv *.txt *.xlsx *.xls"),
                ("Text Files", "*.csv *.tsv *.txt"),
                ("Excel Files", "*.xlsx *.xls"),
                ("All Files", "*.*")
            ]
        )
        if not filepath:
            return

        is_valid, msg = self.file_loader.validate_file(filepath)
        if not is_valid:
            messagebox.showerror("Invalid File", msg)
            return
            
        self.root.title(f"Payload Diff Viewer - {os.path.basename(filepath)}")
        self.status_var.set(f"Loading {filepath}...")
        
        # Show progress dialog
        progress_dialog, pbar, status_var = self._show_loading_progress("Loading File")
        
        def progress_callback(percent: float | None, status: str):
            """Thread-safe UI update callback."""
            def update():
                if not progress_dialog.winfo_exists():
                    return # Dialog was closed
                status_var.set(status)
                if percent is None:
                    pbar.config(mode='indeterminate')
                    pbar.start(10)
                else:
                    pbar.config(mode='determinate', value=percent)
                    pbar.stop()
            self.root.after(0, update)

        def load_task():
            """The actual file loading work in a separate thread."""
            try:
                self.parse_logger.info(f"Starting file load: {filepath}")
                headers, rows = self.file_loader.load_any(filepath, progress_callback)
                self.parse_logger.info(f"File loaded. {len(rows)} rows, {len(headers)} columns.")
                
                # Send data back to main thread
                self.root.after(0, self._on_file_loaded, headers, rows)
                
            except Exception as e:
                self.parse_logger.error(f"File load failed: {e}")
                self.root.after(
                    0, 
                    messagebox.showerror, 
                    "Load Error", 
                    f"Failed to load file:\n{e}"
                )
            finally:
                # Close progress dialog
                self.root.after(0, progress_dialog.destroy)
                self.root.after(0, self.status_var.set, "Load complete.")

        # Start the loading thread
        threading.Thread(target=load_task, daemon=True).start()

    def _on_file_loaded(self, headers: List[str], rows: List[List[Any]]):
        """
        Callback executed on the main thread after file is loaded.
        """
        if not headers or not rows:
            self.status_var.set("File loaded, but no data found.")
            self.parse_logger.warn("File load resulted in no data.")
            return
            
        self.headers = headers
        self.raw_rows = rows
        
        # Create DataFrame for analysis
        if PANDAS_AVAILABLE:
            self.status_var.set("Creating DataFrame...")
            self.root.update_idletasks()
            try:
                self.full_data_df = pd.DataFrame(rows, columns=headers)
                self.parse_logger.info(f"DataFrame created with shape {self.full_data_df.shape}")
            except Exception as e:
                self.parse_logger.error(f"Failed to create DataFrame: {e}")
                self.full_data_df = None
        else:
            self.full_data_df = None
            
        self.row_count_var.set(f"Rows: {len(rows)}")
        self.status_var.set(f"File loaded: {len(rows)} rows.")
        
        self._update_comboboxes()
        # Clear old diff results
        self.diff_tree.delete(*self.diff_tree.get_children())
        self.current_diff_results = {}
        self.diff_data_map = {}
        
        # Close any open summary window, as data is stale
        if self.summary_window and self.summary_window.winfo_exists():
            self.summary_window.destroy()
            self.summary_window = None

    def run_compare(self):
        """
        Runs the comparison process for all rows based on selected columns.
        """
        if not self.raw_rows:
            messagebox.showwarning("No Data", "Please open a file first.")
            return
            
        # Get selected column names
        cols = {key: var.get() for key, var in self.column_vars.items()}
        if not all(cols.values()):
            messagebox.showerror("Error", "Please select all four columns (Name, Key, Old, New).")
            return
            
        try:
            # Get column indices
            name_idx = self.headers.index(cols["config_name"])
            key_idx = self.headers.index(cols["config_key"])
            old_idx = self.headers.index(cols["old_payload"])
            new_idx = self.headers.index(cols["new_payload"])
        except ValueError as e:
            messagebox.showerror("Column Error", f"Invalid column name selected: {e}")
            return

        self.status_var.set("Comparing payloads...")
        self.compare_progress.pack(side=tk.LEFT, padx=5, pady=5)
        self.compare_progress.start(10)
        self.root.update_idletasks()
        
        self.diff_tree.delete(*self.diff_tree.get_children())
        self.current_diff_results = {}
        self.diff_data_map = {}
        
        # Store params for re-filtering
        self._last_compare_params = (name_idx, key_idx, old_idx, new_idx)
        
        # --- Run comparison in a thread ---
        # This is CPU-bound, so threading is appropriate
        
        q = queue.Queue() # Queue for thread-safe UI updates
        
        def compare_task():
            """Worker thread for running comparisons row by row."""
            total_rows = len(self.raw_rows)
            diffs_found = 0
            
            try:
                for i, row in enumerate(self.raw_rows):
                    if (i % 50 == 0) or (i == total_rows - 1):
                        progress = (i + 1) / total_rows * 100
                        # Send progress update
                        q.put(("progress", progress, f"Comparing row {i+1}/{total_rows}"))
                    
                    cfg_name = str(row[name_idx])
                    cfg_key = str(row[key_idx])
                    old_payload_str = row[old_idx]
                    new_payload_str = row[new_idx]
                    
                    # Parse JSON
                    old_obj, old_err = try_parse_json(old_payload_str)
                    if old_err:
                        self.parse_logger.warn(f"[{cfg_name}|{cfg_key}] Old payload parse error: {old_err}")
                        old_obj = old_payload_str # Treat as raw text
                        
                    new_obj, new_err = try_parse_json(new_payload_str)
                    if new_err:
                        self.parse_logger.warn(f"[{cfg_name}|{cfg_key}] New payload parse error: {new_err}")
                        new_obj = new_payload_str # Treat as raw text
                        
                    # We store the *parsed* objects for the summary view
                    # and the *original* strings for the full text view
                    row_data = {
                        "cfg_name": cfg_name,
                        "cfg_key": cfg_key,
                        "old_parsed": old_obj,
                        "new_parsed": new_obj,
                        "old_raw": old_payload_str if old_payload_str is not None else "",
                        "new_raw": new_payload_str if new_payload_str is not None else "",
                    }
                    
                    # Run DeepDiff (on parsed objects)
                    # Get settings from main thread via UI vars
                    # This is generally safe as they are tk.StringVar
                    ignore_order = self.ignore_order_var.get()
                    coerce_numeric = self.coerce_numeric_var.get()
                    
                    diff = run_deepdiff(
                        old_obj, 
                        new_obj, 
                        ignore_order=ignore_order,
                        coerce_numeric=coerce_numeric
                    )
                    
                    if diff:
                        diffs_found += 1
                        row_data["diff"] = diff
                        # Send diff data back for insertion
                        q.put(("diff_row", row_data))
                
                q.put(("done", f"Compare finished. {diffs_found} configs have diffs."))
                
            except Exception as e:
                import traceback
                self.parse_logger.error(f"Compare thread error: {traceback.format_exc()}")
                q.put(("error", str(e)))
        
        # Start the task
        threading.Thread(target=compare_task, daemon=True).start()
        
        # Start processing the queue on the main thread
        self._process_compare_queue(q)
        
    def _process_compare_queue(self, q: queue.Queue):
        """Polls the queue for updates from the compare thread."""
        try:
            msg = q.get_nowait()
            msg_type = msg[0]
            
            if msg_type == "progress":
                _, percent, status = msg
                self.status_var.set(status)
                self.compare_progress.config(mode='determinate', value=percent)
                
            elif msg_type == "diff_row":
                _, row_data = msg
                # Store data for filtering
                self.current_diff_results[row_data["cfg_key"]] = row_data
                # We defer populating the table to avoid UI lag
                # We'll populate it all at the end in the "done" block

            elif msg_type == "done":
                _, status = msg
                self.status_var.set(status)
                self.compare_progress.stop()
                self.compare_progress.pack_forget()
                self.parse_logger.info(status)
                # Now, populate the table
                self.status_var.set("Populating diff table...")
                self.root.update_idletasks()
                self._populate_diff_table() # This will apply filters
                self.status_var.set(status)
                return # Stop polling
            
            elif msg_type == "error":
                _, error_msg = msg
                messagebox.showerror("Compare Error", f"An error occurred: {error_msg}")
                self.status_var.set(f"Error: {error_msg}")
                self.compare_progress.stop()
                self.compare_progress.pack_forget()
                return # Stop polling

        except queue.Empty:
            pass # No message, just wait
            
        # Reschedule processing
        self.root.after(100, self._process_compare_queue, q)
        
    def _schedule_filter_update(self, *args):
        """Debounces calls to _populate_diff_table to avoid lag on typing."""
        if self._filter_job:
            self.root.after_cancel(self._filter_job)
        self._filter_job = self.root.after(300, self._populate_diff_table)

    def _populate_diff_table(self):
        """
        Clears and repopulates the diff table based on
        self.current_diff_results and current filter/watch settings.
        """
        self.status_var.set("Applying filters and populating table...")
        self.root.update_idletasks()
        
        self.diff_tree.delete(*self.diff_tree.get_children())
        self.diff_data_map.clear()
        
        if not self.current_diff_results:
            self.status_var.set("No diffs found or compare not run.")
            return
            
        filter_text = self.filter_var.get().lower()
        watch_list = {
            k.strip().lower() 
            for k in self.watch_list_var.get().split(',') 
            if k.strip()
        }
        watch_only = self.watch_only_var.get()
        
        # Get diffs in a stable order
        sorted_keys = sorted(self.current_diff_results.keys())
        
        item_count = 0
        
        for cfg_key in sorted_keys:
            row_data = self.current_diff_results[cfg_key]
            cfg_name = row_data["cfg_name"]
            diff = row_data["diff"]
            
            # --- Iterate over diffs and flatten ---
            for change_type, changes in diff.items():
                if change_type not in (
                    'values_changed', 
                    'dictionary_item_added', 
                    'dictionary_item_removed',
                    'iterable_item_added',
                    'iterable_item_removed'
                ):
                    continue
                
                # 'changes' is a list for set/iterable diffs, or dict for value/dict diffs
                if isinstance(changes, dict):
                    items_to_iterate = changes.items()
                elif isinstance(changes, list):
                    items_to_iterate = [(item, None) for item in changes] # (path, diff_obj)
                else:
                    continue

                for path, diff_obj in items_to_iterate:
                    # Clean path: "root['key'][0]" -> "key[0]"
                    clean_path = path.replace("root", "").strip("[]'")
                    
                    is_watch_item = any(watch_key in clean_path.lower() for watch_key in watch_list)
                    
                    if watch_only and not is_watch_item:
                        continue
                        
                    # Apply text filter
                    search_str = f"{cfg_name} {cfg_key} {change_type} {clean_path}".lower()
                    if filter_text and filter_text not in search_str:
                        continue
                        
                    tags = []
                    if change_type == 'values_changed':
                        tags.append("changed")
                        old_val = diff_obj['old_value']
                        new_val = diff_obj['new_value']
                        # Special handling for "975" vs 975 as requested
                        # We get the *original* values from the *original* data
                        orig_old = self._get_value_from_path(row_data["old_parsed"], path)
                        orig_new = self._get_value_from_path(row_data["new_parsed"], path)
                        
                        old_display = f"{orig_old} ({type(orig_old).__name__})"
                        new_display = f"{orig_new} ({type(orig_new).__name__})"
                        
                    elif 'added' in change_type:
                        tags.append("added")
                        old_val = ""
                        old_display = "---"
                        new_val = diff_obj['new_value'] if isinstance(diff_obj, dict) else path
                        new_display = str(new_val)
                    
                    elif 'removed' in change_type:
                        tags.append("removed")
                        old_val = diff_obj['old_value'] if isinstance(diff_obj, dict) else path
                        old_display = str(old_val)
                        new_val = ""
                        new_display = "---"
                    
                    if is_watch_item:
                        tags.append("watch")
                        
                    # Data for the table row
                    values = (
                        f"{cfg_name} | {cfg_key}",
                        change_type,
                        clean_path,
                        old_display,
                        new_display
                    )
                    
                    item_id = self.diff_tree.insert("", "end", values=values, tags=tuple(tags))
                    item_count += 1
                    
                    # Store all data needed for selection
                    self.diff_data_map[item_id] = {
                        "cfg_key": cfg_key, # Key to find full payloads
                        "path": path,       # Full DeepDiff path (e.g., "root['key']")
                        "old_val": old_val, # Raw values for inline
                        "new_val": new_val,
                    }

        self.status_var.set(f"Compare complete. Displaying {item_count} diffs.")

    def _get_value_from_path(self, obj: Any, path: str) -> Any:
        """
        Safely retrieves a value from a nested object using a DeepDiff path string.
        e.g., obj, "root['users'][0]['name']"
        """
        try:
            # This is a safe-ish eval for the path format
            if path == "root":
                return obj
            
            # Use DeepDiff's built-in extractor
            from deepdiff.path import extract
            return extract(obj, path)
            
        except Exception:
            # Fallback for paths DeepDiff produces for lists, e.g. "root[0]"
            try:
                # 'root' is just a placeholder
                current = obj
                # "root['key'][0]" -> "['key'][0]"
                indices = re.findall(r"\[(.*?)]", path)
                for index in indices:
                    index_cleaned = index.strip("'\"")
                    if index_cleaned.isdigit():
                        current = current[int(index_cleaned)]
                    else:
                        current = current[index_cleaned]
                return current
            except Exception as e:
                self.parse_logger.warn(f"Could not get value for path '{path}': {e}")
                return "[Error: Path not found]"

    def on_diff_row_selected(self, event: Any):
        """
        Handles selection of a row in the diff table.
        Updates inline diffs and highlights full JSON panes.
        """
        selection = self.diff_tree.selection()
        if not selection:
            return
            
        item_id = selection[0]
        if item_id not in self.diff_data_map:
            return
            
        data = self.diff_data_map[item_id]
        
        # 1. Get full payloads
        full_payload_data = self.current_diff_results.get(data["cfg_key"])
        if not full_payload_data:
            return

        # 2. Update Inline Diffs
        old_inline = json_to_pretty_text(data["old_val"])
        new_inline = json_to_pretty_text(data["new_val"])
        self._set_text_widget(self.inline_old_text, old_inline)
        self._set_text_widget(self.inline_new_text, new_inline)
        
        # 3. Update Full JSON Panes
        old_full_text = json_to_pretty_text(full_payload_data["old_parsed"])
        new_full_text = json_to_pretty_text(full_payload_data["new_parsed"])
        self._set_text_widget(self.text_old, old_full_text)
        self._set_text_widget(self.text_new, new_full_text)
        
        # 4. Find and Highlight
        
        # 'path' is like "root['key_name']" or "root[0]"
        path = data["path"]
        
        # Extract the *last* key for regex search
        key_match = re.findall(r"['\"](.*?)['\"]", path)
        key_name = key_match[-1] if key_match else None
        
        if key_name:
            # Create regex: r'"key_name"\s*:'
            key_regex = rf'"{re.escape(key_name)}"\s*:'
            
            # Create value hints
            old_val_hint = json.dumps(data["old_val"], ensure_ascii=False) if data["old_val"] else None
            new_val_hint = json.dumps(data["new_val"], ensure_ascii=False) if data["new_val"] else None
            
            # Find in OLD pane
            self._find_and_highlight(
                self.text_old, 
                key_regex, 
                old_val_hint
            )
            # Find in NEW pane
            self._find_and_highlight(
                self.text_new, 
                key_regex, 
                new_val_hint
            )
            
        else:
            # Probably an array change, e.g., "root[0]"
            # Try to highlight just based on value
            old_val_hint = json.dumps(data["old_val"], ensure_ascii=False) if data["old_val"] else None
            new_val_hint = json.dumps(data["new_val"], ensure_ascii=False) if data["new_val"] else None
            
            if old_val_hint and old_val_hint not in ('null', '""'):
                self._find_and_highlight(self.text_old, re.escape(old_val_hint), None)
            if new_val_hint and new_val_hint not in ('null', '""'):
                 self._find_and_highlight(self.text_new, re.escape(new_val_hint), None)

    def _set_text_widget(self, text_widget: tk.Text, content: str):
        """Helper to safely update a text widget's content."""
        try:
            text_widget.config(state="normal")
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", content)
            text_widget.config(state="disabled")
        except tk.TclError as e:
            self.parse_logger.warn(f"Error setting text widget: {e}")

    def _find_and_highlight(
        self, 
        text_widget: tk.Text, 
        key_regex: str, 
        value_hint: str | None
    ):
        """Finds the line in the text widget and applies 'hit' tag."""
        text_widget.tag_remove('hit', '1.0', tk.END)
        
        full_text = text_widget.get("1.0", tk.END)
        if not full_text.strip():
            return
            
        line_num = find_line_index(full_text, key_regex, value_hint)
        
        if line_num:
            try:
                # Apply tag and scroll
                line_start = f"{line_num}.0"
                line_end = f"{line_num}.end"
                
                text_widget.tag_add('hit', line_start, line_end)
                
                # Scroll into view
                # We use yview_moveto to sync, so just see() one
                text_widget.see(line_start)
                
                # Manually trigger the scroll sync
                # This ensures both panes move
                current_view = text_widget.yview()
                if text_widget == self.text_old:
                    self._on_text_scroll_old(*current_view)
                else:
                    self._on_text_scroll_new(*current_view)
                    
            except tk.TclError as e:
                self.parse_logger.warn(f"Error highlighting line {line_num}: {e}")
        else:
            self.parse_logger.info(f"Highlight: No line found for regex='{key_regex}'")

    # --- Menu Actions ---

    def set_default_folder(self):
        """Opens folder picker to set the default open directory."""
        new_dir = filedialog.askdirectory(
            title="Select Default Folder",
            initialdir=self.settings.get("default_open_dir", os.path.expanduser("~"))
        )
        if new_dir:
            self.settings.set("default_open_dir", new_dir)
            self.settings.save()
            self.status_var.set(f"Default folder set to: {new_dir}")
            
    def set_default_sharepoint(self):
        """Opens string prompt to set a SharePoint URL as default."""
        url = simpledialog.askstring(
            "SharePoint URL",
            "Enter the full SharePoint/OneDrive URL to your folder:",
            parent=self.root
        )
        if url and url.startswith("http"):
            self.settings.set("default_open_dir", url)
            self.settings.save()
            self.status_var.set(f"Default path set to SharePoint URL: {url}")
            # Test resolution
            self.root.after(100, self._test_sharepoint_url, url)
        elif url:
            messagebox.showwarning("Invalid URL", "URL must start with 'http://' or 'https://'.")

    def _test_sharepoint_url(self, url: str):
        """BG test to see if a SP URL can be resolved."""
        self.status_var.set("Testing SharePoint URL resolution...")
        self.root.update_idletasks()
        
        def test_task():
            unc_path = sharepoint_url_to_unc(url)
            if unc_path:
                self.parse_logger.info(f"SharePoint URL resolved successfully to {unc_path}")
                self.root.after(
                    0, 
                    self.status_var.set, 
                    "SharePoint URL resolved successfully."
                )
            else:
                self.parse_logger.warn(f"Failed to resolve SharePoint URL: {url}")
                self.root.after(
                    0,
                    self.status_var.set,
                    "Warning: Could not resolve SharePoint URL. Check access/VPN."
                )
        
        threading.Thread(target=test_task, daemon=True).start()

    def export_diff_table(self):
        """Exports the *current* view of the diff table to CSV."""
        if not self.diff_tree.get_children():
            messagebox.showwarning("Export Error", "No diff data to export.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Diff Table As",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt")],
            defaultextension=".csv"
        )
        if not save_path:
            return

        try:
            with open(save_path, 'w', encoding='utf-8', newline='') as f:
                import csv
                writer = csv.writer(f)
                
                # Write headers
                headers = ui_config.DIFF_TABLE_COLUMNS.keys()
                writer.writerow(headers)
                
                # Write rows
                for item_id in self.diff_tree.get_children():
                    row_values = self.diff_tree.item(item_id, 'values')
                    writer.writerow(row_values)
                    
            self.status_var.set(f"Diff table exported to {save_path}")
            messagebox.showinfo("Export Successful", f"Diff table saved to:\n{save_path}")
            
        except IOError as e:
            messagebox.showerror("Export Error", f"Failed to write file: {e}")

    def show_summary(self):
        """Opens the Summary Dashboard window."""
        if not PANDAS_AVAILABLE:
            messagebox.showerror(
                "Missing Dependency",
                "The 'pandas' library is required for the Summary Dashboard."
            )
            return
            
        if self.full_data_df is None:
            messagebox.showwarning(
                "No Data",
                "Please open a file and run a comparison before viewing the summary."
            )
            return
            
        config_name_col = self.column_vars["config_name"].get()
        if not config_name_col:
            messagebox.showerror("Error", "Please select a 'Config Name' column first.")
            return

        # Check if window already exists
        if self.summary_window and self.summary_window.winfo_exists():
            self.summary_window.lift()
        else:
            try:
                # Pass the *original* df with *all* rows, not just diffs
                self.summary_window = SummaryDashboard(
                    self.root, 
                    self.full_data_df, 
                    config_name_col
                )
            except Exception as e:
                messagebox.showerror("Summary Error", f"Could not open Summary window: {e}")
                self.parse_logger.error(f"Summary window failed: {e}")

    def show_about(self):
        """Displays a simple about message box."""
        messagebox.showinfo(
            "About Payload Diff Viewer",
            "Payload Diff Viewer\n\n"
            "A desktop tool for comparing JSON payloads.\n"
            "Built with Python, Tkinter, DeepDiff, and Pandas."
        )