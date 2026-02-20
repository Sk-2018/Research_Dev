# payload_viewer/app.py
from __future__ import annotations

# ── Built-ins
import os
import sys
import json
import threading
import queue
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── Third-party (optional fallbacks handled at runtime)
try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

# Matplotlib (optional)
HAS_MPL = True
try:
    import matplotlib
    matplotlib.use("TkAgg")  # embed into Tk
    from matplotlib import pyplot as plt  # type: ignore
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # type: ignore
except Exception:  # pragma: no cover
    HAS_MPL = False
    plt = None  # type: ignore
    FigureCanvasTkAgg = None  # type: ignore

# ── Tkinter
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ── Internal modules
from .parse_logger import ParseLogger
from .settings import SettingsManager
from .ui_config import UIConfig
from .file_loader import FileLoader
from .json_utils import (
    json_to_pretty_text,
    try_parse_json,
    stringify_for_diff,
)
from .diff_engine import run_deepdiff


# ============================================================
# Utilities
# ============================================================
def coerce_maybe_number(s: Any) -> Any:
    """
    Used in inline rendering so numeric-like strings don't appear as different
    when only the textual representation differs (e.g. "1" vs 1).
    """
    if isinstance(s, str):
        try:
            if re.fullmatch(r"-?\d+", s):
                return int(s)
            if re.fullmatch(r"-?\d+\.\d+", s):
                return float(s)
        except Exception:
            return s
    return s


# ============================================================
# Safe synced scrolling for the full JSON panes
# ============================================================
class SyncedTextPair:
    """Synchronize vertical scrolling between two Text widgets safely."""

    def __init__(
        self,
        left: tk.Text,
        right: tk.Text,
        left_vsb: Optional[ttk.Scrollbar] = None,
        right_vsb: Optional[ttk.Scrollbar] = None,
    ) -> None:
        self.left = left
        self.right = right
        self._syncing = False

        # Save original yview callables
        self._left_yview = left.yview
        self._right_yview = right.yview

        # Wrap yview on both widgets
        def left_yview(*args):
            if self._syncing:
                return self._left_yview(*args)
            self._syncing = True
            try:
                self._left_yview(*args)
                self._right_yview(*args)
            finally:
                self._syncing = False

        def right_yview(*args):
            if self._syncing:
                return self._right_yview(*args)
            self._syncing = True
            try:
                self._right_yview(*args)
                self._left_yview(*args)
            finally:
                self._syncing = False

        left.yview = left_yview          # type: ignore[attr-defined]
        right.yview = right_yview        # type: ignore[attr-defined]

        # Each text updates only its own scrollbar
        if left_vsb is not None:
            left.configure(yscrollcommand=left_vsb.set)
            left_vsb.configure(command=self._on_left_scrollbar)
        if right_vsb is not None:
            right.configure(yscrollcommand=right_vsb.set)
            right_vsb.configure(command=self._on_right_scrollbar)

        # Mouse wheels scroll both
        for w in (left, right):
            w.bind("<MouseWheel>", self._on_mousewheel, add="+")
            w.bind("<Button-4>", self._on_mousewheel, add="+")
            w.bind("<Button-5>", self._on_mousewheel, add="+")

    def _on_left_scrollbar(self, *args):
        self.left.yview(*args)
        self.right.yview(*args)

    def _on_right_scrollbar(self, *args):
        self.right.yview(*args)
        self.left.yview(*args)

    def _on_mousewheel(self, event):
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = -1 * int(event.delta / 120)
        self.left.yview_scroll(delta, "units")
        self.right.yview_scroll(delta, "units")
        return "break"


# ============================================================
# App
# ============================================================
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Payload Diff Viewer (Config Name -> Current vs Old)")
        self.geometry(UIConfig.DEFAULT_GEOMETRY)

        # Managers
        self.settings = SettingsManager()
        self.parse_logger = ParseLogger()

        # Loader
        self.loader = FileLoader(self.parse_logger)

        # State
        self.loaded_df: Optional["pd.DataFrame"] = None
        self.current_config_name: Optional[str] = None

        # Build UI
        self._build_ui()

        # Key binds
        self.bind("<Control-o>", lambda *_: self.on_open())
        self.bind("<Control-m>", lambda *_: self.on_view_summary())

    # ---------------- UI construction ----------------
    def _build_ui(self) -> None:
        # Menus
        menubar = tk.Menu(self)
        # File
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open…    Ctrl+O", command=self.on_open)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)
        # View
        viewmenu = tk.Menu(menubar, tearoff=0)
        viewmenu.add_command(label="Summary…    Ctrl+M", command=self.on_view_summary)
        menubar.add_cascade(label="View", menu=viewmenu)
        # Help
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Show Parse Log", command=lambda: self.parse_logger.show(self))
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.config(menu=menubar)

        # Top row
        top = ttk.Frame(self); top.pack(fill=tk.X, padx=10, pady=8)
        ttk.Button(top, text="Open…", command=self.on_open).pack(side=tk.LEFT)

        ttk.Label(top, text="Config Name:").pack(side=tk.LEFT, padx=(12, 4))
        self.cmb_name = ttk.Combobox(top, state="disabled", width=36)
        self.cmb_name.pack(side=tk.LEFT)
        self.cmb_name.bind("<<ComboboxSelected>>", lambda *_: self._on_cfg_name_change())

        ttk.Label(top, text="Config Keys:").pack(side=tk.LEFT, padx=(12, 4))
        self.lst_keys = tk.Listbox(top, selectmode=tk.EXTENDED, width=38, height=6, exportselection=False)
        self.lst_keys.configure(state=tk.DISABLED)
        self.lst_keys.pack(side=tk.LEFT)

        # Buttons
        actions = ttk.Frame(top); actions.pack(side=tk.LEFT, padx=(12, 0))
        self.btn_compare = ttk.Button(actions, text="Compare (F5)", state="disabled", command=self.on_compare)
        self.btn_compare.pack()
        self.btn_clear = ttk.Button(actions, text="Clear Results", state="disabled", command=self._reset_views)
        self.btn_clear.pack(pady=(4, 0))

        # Filter row
        flt = ttk.Frame(self); flt.pack(fill=tk.X, padx=10, pady=2)
        ttk.Label(flt, text="Filter:").pack(side=tk.LEFT)
        self.filter_entry = ttk.Entry(flt, width=40)
        self.filter_entry.pack(side=tk.LEFT, padx=8)
        ttk.Button(flt, text="Clear", command=lambda: self.filter_entry.delete(0, tk.END)).pack(side=tk.LEFT)

        # Diff table
        ftable = ttk.Frame(self); ftable.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 6))
        cols = ("CfgKey", "Type", "Key", "Old", "New")
        self.tree = ttk.Treeview(ftable, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=UIConfig.TREE_WIDTHS.get(c, 180), anchor="w")
        vsb = ttk.Scrollbar(ftable, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(ftable, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        ftable.rowconfigure(0, weight=1); ftable.columnconfigure(0, weight=1)

        # Inline diff
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL); paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        fmid = ttk.LabelFrame(paned, text="Selected Field - Inline Diff"); paned.add(fmid, weight=1)
        left = ttk.Frame(fmid); left.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        right = ttk.Frame(fmid); right.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        fmid.columnconfigure(0, weight=1); fmid.columnconfigure(1, weight=1); fmid.rowconfigure(1, weight=1)

        ttk.Label(left, text="OLD").pack(anchor="w")
        self.txt_sel_old = tk.Text(left, wrap="word", height=UIConfig.INLINE_ROWS, font=("Courier New", 9))
        self.txt_sel_old.pack(fill=tk.BOTH, expand=True)
        ttk.Label(right, text="CURRENT").pack(anchor="w")
        self.txt_sel_new = tk.Text(right, wrap="word", height=UIConfig.INLINE_ROWS, font=("Courier New", 9))
        self.txt_sel_new.pack(fill=tk.BOTH, expand=True)

        # Full JSON panes
        fbot = ttk.Frame(paned); paned.add(fbot, weight=2)
        jl = ttk.LabelFrame(fbot, text="OLD Payload (Full JSON)"); jl.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        jr = ttk.LabelFrame(fbot, text="CURRENT Payload (Full JSON)"); jr.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        fbot.columnconfigure(0, weight=1); fbot.columnconfigure(1, weight=1); fbot.rowconfigure(0, weight=1)

        # OLD
        self.txt_old = tk.Text(jl, wrap="none", font=("Courier New", 9))
        sc1y = ttk.Scrollbar(jl, orient="vertical")
        sc1x = ttk.Scrollbar(jl, orient="horizontal")
        self.txt_old.configure(yscrollcommand=sc1y.set, xscrollcommand=sc1x.set)
        sc1y.configure(command=self.txt_old.yview)
        sc1x.configure(command=self.txt_old.xview)
        self.txt_old.pack(fill=tk.BOTH, expand=True)
        sc1y.pack(side=tk.RIGHT, fill=tk.Y)
        sc1x.pack(side=tk.BOTTOM, fill=tk.X)

        # CURRENT
        self.txt_cur = tk.Text(jr, wrap="none", font=("Courier New", 9))
        sc2y = ttk.Scrollbar(jr, orient="vertical")
        sc2x = ttk.Scrollbar(jr, orient="horizontal")
        self.txt_cur.configure(yscrollcommand=sc2y.set, xscrollcommand=sc2x.set)
        sc2y.configure(command=self.txt_cur.yview)
        sc2x.configure(command=self.txt_cur.xview)
        self.txt_cur.pack(fill=tk.BOTH, expand=True)
        sc2y.pack(side=tk.RIGHT, fill=tk.Y)
        sc2x.pack(side=tk.BOTTOM, fill=tk.X)

        # Synchronize vertical scrolling
        self.sync_pair = SyncedTextPair(self.txt_old, self.txt_cur, sc1y, sc2y)

    # ---------------- File open ----------------
    def on_open(self) -> None:
        initial_dir = self.settings.get("default_open_dir") or os.getcwd()
        path = filedialog.askopenfilename(
            parent=self,
            title="Open CSV/TSV/TXT or Excel",
            initialdir=initial_dir,
            filetypes=[
                ("Spreadsheet", "*.xlsx;*.xls"),
                ("Delimited text", "*.csv;*.tsv;*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        # Progress dialog
        dlg = _Progress(self, "Loading Excel…" if path.lower().endswith((".xlsx", ".xls")) else "Loading file…")
        dlg.set_status("Starting…")

        def worker():
            try:
                headers, rows = self.loader.load_any(path, progress_cb=dlg.update_progress)
                # Build DataFrame for summary/dashboard
                if pd is not None:
                    try:
                        self.loaded_df = pd.DataFrame(rows, columns=headers)
                    except Exception:
                        # best effort
                        self.loaded_df = pd.DataFrame([{h: r[i] if i < len(r) else None for i, h in enumerate(headers)} for r in rows])
                else:
                    self.loaded_df = None
                self.parse_logger.info(f"Loaded {len(rows)} rows.")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during loading:\n{e}"))
            finally:
                self.after(0, dlg.close)

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- Compare (placeholder wiring to your engine) ----------------
    def on_compare(self) -> None:
        # This is a minimal glue; your real app likely builds old_obj/cur_obj from the rows.
        try:
            old_obj = try_parse_json(self.txt_old.get("1.0", tk.END))[0]
            cur_obj = try_parse_json(self.txt_cur.get("1.0", tk.END))[0]
        except Exception:
            old_obj = self.txt_old.get("1.0", tk.END)
            cur_obj = self.txt_cur.get("1.0", tk.END)

        ignore_order = False
        # Backwards/forwards compatible DeepDiff call
        try:
            dd = run_deepdiff(old_obj, cur_obj, ignore_order=ignore_order, coerce_numeric=True)  # new signature
        except TypeError:
            dd = run_deepdiff(old_obj, cur_obj, ignore_order=ignore_order)  # old signature

        # ... use dd for your table; left as-is to keep focus on summary/scroll ...

    # ---------------- Summary Dashboard ----------------
    def on_view_summary(self) -> None:
        if self.loaded_df is None or (pd is None):
            messagebox.showinfo("Summary", "Open a file first (pandas required).")
            return
        SummaryWindow(self, self.loaded_df, self.parse_logger)


# ============================================================
# Summary Window
# ============================================================
class SummaryWindow(tk.Toplevel):
    """
    Pivot summary: Config Name | Count
    - Grand Total row
    - Chart shows only selected rows (if selection != 0); otherwise Top-N
    - Export CSV / Save PNG
    """

    def __init__(self, master: tk.Tk, df: "pd.DataFrame", logger: ParseLogger) -> None:
        super().__init__(master)
        self.logger = logger
        self.title("Summary: Rows per Config Name")
        self.geometry("1100x650")

        self.df = df
        self._after_id: Optional[str] = None

        # Controls bar
        bar = ttk.Frame(self); bar.pack(fill=tk.X, padx=10, pady=(10, 6))

        ttk.Label(bar, text="Top N:").pack(side=tk.LEFT)
        self.topn_var = tk.IntVar(value=25)
        tk.Spinbox(bar, from_=5, to=1000, increment=1, width=6, textvariable=self.topn_var,
                   command=self._schedule_render).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(bar, text="Max label length:").pack(side=tk.LEFT)
        self.maxlbl_var = tk.IntVar(value=80)
        tk.Spinbox(bar, from_=10, to=200, increment=5, width=6, textvariable=self.maxlbl_var,
                   command=self._schedule_render).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(bar, text="Export Summary CSV", command=self._export_csv).pack(side=tk.RIGHT, padx=(6, 0))
        if HAS_MPL:
            ttk.Button(bar, text="Save Chart PNG", command=self._save_png).pack(side=tk.RIGHT)

        # Split
        body = ttk.Frame(self); body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        body.columnconfigure(0, weight=1); body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Table
        table_frame = ttk.Frame(body); table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.tree = ttk.Treeview(table_frame, columns=("Config Name", "Count"), show="headings", selectmode="extended")
        self.tree.heading("Config Name", text="Config Name")
        self.tree.heading("Count", text="Count")
        self.tree.column("Config Name", width=420, anchor="w")
        self.tree.column("Count", width=80, anchor="e")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1); table_frame.columnconfigure(0, weight=1)

        # Chart area
        chart_frame = ttk.Frame(body); chart_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.chart_frame = chart_frame

        # Build pivot
        self._pivot_df = self._build_pivot(self.df)
        self._populate_table(self._pivot_df)

        # Selection updates chart
        self.tree.bind("<<TreeviewSelect>>", lambda *_: self._render_chart())

        # Initial chart
        self._render_chart()

    def _build_pivot(self, df: "pd.DataFrame") -> "pd.DataFrame":
        # Heuristic: find a column that looks like config name (letters+underscore only)
        col_candidates = [c for c in df.columns if re.fullmatch(r"[A-Za-z_]+", str(c or ""))]
        if not col_candidates:
            # Fall back to the first column
            cfg_col = df.columns[0]
        else:
            # Choose the one with most uniques
            cfg_col = max(col_candidates, key=lambda c: df[c].astype(str).nunique(dropna=True))

        # Value cleaning to keep only alphabetic_with_underscore names
        def clean_val(v: Any) -> str:
            s = str(v) if v is not None else ""
            m = re.search(r"[A-Za-z_]+", s)
            return m.group(0) if m else s

        series = df[cfg_col].map(clean_val)

        pivot = series.value_counts(dropna=False).rename_axis("Config Name").reset_index(name="Count")
        pivot = pivot.sort_values(["Count", "Config Name"], ascending=[False, True], ignore_index=True)

        # Add Grand Total
        total = int(pivot["Count"].sum())
        grand = pd.DataFrame([{"Config Name": "Grand Total", "Count": total}])
        # Keep label as last row
        pivot_with_total = pd.concat([pivot, grand], ignore_index=True)
        return pivot_with_total

    def _populate_table(self, pvt: "pd.DataFrame") -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for _, row in pvt.iterrows():
            tags = ()
            if str(row["Config Name"]).lower() == "grand total":
                tags = ("grand",)
            self.tree.insert("", tk.END, values=(row["Config Name"], int(row["Count"])), tags=tags)
        # Style for Grand Total
        self.tree.tag_configure("grand", background="#f2f2f2", font=("Segoe UI", 9, "bold"))

    def _selected_dataframe(self) -> "pd.DataFrame":
        """Return dataframe for chart: selected rows (excluding Grand Total) or Top-N."""
        sel = self.tree.selection()
        if sel:
            labels = []
            for iid in sel:
                name, cnt = self.tree.item(iid, "values")
                if str(name).lower() == "grand total":
                    continue
                labels.append((str(name), int(cnt)))
            if labels:
                return pd.DataFrame(labels, columns=["Config Name", "Count"])
        # No selection → use Top-N (excluding Grand Total)
        base = self._pivot_df[self._pivot_df["Config Name"].str.lower() != "grand total"]
        n = max(1, int(self.topn_var.get()))
        return base.head(n)

    def _render_chart(self) -> None:
        if not HAS_MPL:
            # Replace chart area content with a friendly message
            for w in self.chart_frame.winfo_children():
                w.destroy()
            ttk.Label(self.chart_frame, text="Chart unavailable. Install matplotlib to view the chart.").pack(
                expand=True
            )
            return

        # clear chart frame
        for w in self.chart_frame.winfo_children():
            w.destroy()

        df = self._selected_dataframe().copy()
        # Truncate labels
        maxlen = max(8, int(self.maxlbl_var.get()))
        df["label"] = df["Config Name"].astype(str).map(lambda s: (s if len(s) <= maxlen else s[: maxlen - 1] + "…"))

        fig_w, fig_h, fig_dpi = 6.5, 5.2, 100
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=fig_dpi)  # type: ignore
        ax.barh(df["label"], df["Count"])  # type: ignore
        ax.set_title("Rows per Config Name")
        ax.set_xlabel("Count")
        ax.invert_yaxis()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)  # type: ignore
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Keep for PNG export
        self._last_fig = fig

    def _schedule_render(self) -> None:
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(180, self._render_chart)

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Summary CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            self._pivot_df.to_csv(path, index=False)
            messagebox.showinfo("Export", f"Saved: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _save_png(self) -> None:
        if not HAS_MPL or not hasattr(self, "_last_fig"):
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Chart PNG",
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
        )
        if not path:
            return
        try:
            self._last_fig.savefig(path, dpi=140)  # type: ignore[attr-defined]
            messagebox.showinfo("Chart", f"Saved: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))


# ============================================================
# Simple progress dialog used during loading
# ============================================================
class _Progress(tk.Toplevel):
    def __init__(self, master: tk.Tk, title: str = "Loading…") -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        ttk.Label(self, text=title).pack(padx=16, pady=(14, 6))
        self.pb = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=360, maximum=100)
        self.pb.pack(padx=16, pady=6)
        self.lbl = ttk.Label(self, text="Starting...")
        self.lbl.pack(padx=16, pady=(0, 12))

        self.update_idletasks()
        self.geometry("+%d+%d" % (master.winfo_rootx() + 80, master.winfo_rooty() + 80))

    def set_status(self, msg: str) -> None:
        self.lbl.configure(text=msg)
        self.update_idletasks()

    def update_progress(self, pct: float, message: str | None = None) -> None:
        try:
            v = int(max(0, min(100, pct)))
            self.pb["value"] = v
            if message:
                self.lbl.configure(text=message)
            self.update_idletasks()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
