
from __future__ import annotations
import json, os, queue, threading, re
from dataclasses import dataclass
from typing import Any, Optional
from tkinter import Tk, Toplevel, StringVar, Text, N, S, E, W, BOTH, END, messagebox
from tkinter import ttk, Menu

from .parse_logger import ParseLogger
from .file_loader import FileLoader
from .json_utils import try_parse_json, json_to_pretty_text, escape_path_for_regex, find_line_index, stringify_for_diff
from .diff_engine import run_deepdiff
from .settings import SettingsManager
from .sharepoint import sharepoint_url_to_unc
from .ui_config import CONFIG
from .summary_dashboard import SummaryDashboard
try:
    import pandas as pd
except Exception:
    pd = None  # type: ignore

@dataclass
class LoadedData:
    headers: list[str]
    rows: list[list[Any]]
    df: "pd.DataFrame | None"

class ProgressDialog(Toplevel):
    def __init__(self, master, title: str = "Loading…") -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=360)
        self.label_var = StringVar(value="Starting…")
        ttk.Label(self, textvariable=self.label_var).pack(padx=12, pady=8)
        self.progress.pack(padx=12, pady=(0, 12))
        ttk.Button(self, text="Cancel", command=self._cancel).pack(pady=(0, 8))
        self._cancelled = False
        self.protocol("WM_DELETE_WINDOW", self._cancel)
    def _cancel(self) -> None: self._cancelled = True
    def update_status(self, pct: float, msg: str) -> None:
        self.progress['value'] = max(0, min(100, int(pct * 100))); self.label_var.set(msg); self.update_idletasks()

class SyncedTextPair:
    def __init__(self, left: Text, right: Text, left_vsb: ttk.Scrollbar, right_vsb: ttk.Scrollbar) -> None:
        self.left, self.right = left, right; self._syncing = False
        def left_yview(*args):
            if self._syncing: return
            self._syncing = True
            try: self.left.yview(*args); self.right.yview_moveto(self.left.yview()[0])
            finally: self._syncing = False
        def right_yview(*args):
            if self._syncing: return
            self._syncing = True
            try: self.right.yview(*args); self.left.yview_moveto(self.right.yview()[0])
            finally: self._syncing = False
        left_vsb.configure(command=left_yview); right_vsb.configure(command=right_yview)
        self.left.configure(yscrollcommand=left_vsb.set); self.right.configure(yscrollcommand=right_vsb.set)
        for widget in (self.left, self.right):
            widget.bind("<MouseWheel>", self._on_mousewheel); widget.bind("<Button-4>", self._on_mousewheel); widget.bind("<Button-5>", self._on_mousewheel)
    def _on_mousewheel(self, event) -> str:
        delta = -1 if getattr(event, "delta", 0) > 0 or getattr(event, "num", 0) == 4 else 1
        self.left.yview_scroll(delta, "units"); self.right.yview_moveto(self.left.yview()[0]); return "break"

class ColumnMappingDialog(Toplevel):
    """Lets user map columns when auto-detection fails."""
    def __init__(self, master, headers: list[str], pre: dict[str, Optional[str]] | None = None) -> None:
        super().__init__(master)
        self.title("Select Columns"); self.resizable(False, False); self.grab_set(); self.result: dict[str, Optional[str]] | None = None
        pre = pre or {}
        self.vars = {k: StringVar(value=pre.get(k) or "") for k in ("config_name_col","config_key_col","payload_old","payload_current")}
        frm = ttk.Frame(self); frm.pack(padx=12, pady=12)
        def row(label, key):
            ttk.Label(frm, text=label, width=20, anchor="e").pack(anchor="w")
            cb = ttk.Combobox(frm, values=headers, textvariable=self.vars[key], width=60, state="readonly"); cb.pack(pady=(0,8))
        row("Config Name", "config_name_col"); row("Config Key", "config_key_col"); row("OLD Payload", "payload_old"); row("CURRENT Payload", "payload_current")
        btns = ttk.Frame(frm); btns.pack(fill="x", pady=(6,0))
        ttk.Button(btns, text="OK", command=self._ok).pack(side="right"); ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right", padx=(0,6))
        self.bind("<Escape>", lambda e: self._cancel())
    def _ok(self) -> None:
        self.result = {k: (v.get() or None) for k, v in self.vars.items()}; self.destroy()
    def _cancel(self) -> None:
        self.result = None; self.destroy()

class App(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Payload Diff Viewer"); self.minsize(CONFIG.min_width, CONFIG.min_height); self.configure(bg=CONFIG.bg_main)
        self.logger = ParseLogger(); self.settings = SettingsManager(); self.loader = FileLoader(self.logger)
        self._build_menu(); self._build_ui(); self._bind_keys()
        self.loaded: LoadedData | None = None; self.old_json: Any | None = None; self.new_json: Any | None = None; self.diff_dict: dict[str, Any] | None = None
        self._column_map: dict[str, str | None] | None = None

    def _build_menu(self) -> None:
        menubar = Menu(self)
        filem = Menu(menubar, tearoff=False)
        filem.add_command(label="Open… \tCtrl+O", command=self.open_file)
        filem.add_separator(); filem.add_command(label="Set Default Folder…", command=self._set_default_folder)
        filem.add_command(label="Set Default from SharePoint URL…", command=self._set_default_from_sp)
        filem.add_separator(); filem.add_command(label="Exit", command=self.destroy)
        viewm = Menu(menubar, tearoff=False); viewm.add_command(label="Summary… \tCtrl+M", command=self.open_summary)
        helpm = Menu(menubar, tearoff=False); helpm.add_command(label="Show Parse Log", command=lambda: self.logger.show_viewer(self))
        menubar.add_cascade(label="File", menu=filem); menubar.add_cascade(label="View", menu=viewm); menubar.add_cascade(label="Help", menu=helpm); self.config(menu=menubar)

    def _build_ui(self) -> None:
        root = self; root.grid_columnconfigure(0, weight=1); root.grid_rowconfigure(1, weight=1)
        bar = ttk.Frame(root); bar.grid(row=0, column=0, sticky=E+W, padx=8, pady=6)
        ttk.Button(bar, text="Open", command=self.open_file).pack(side="left"); ttk.Button(bar, text="Compare \tF5", command=self.compare_now).pack(side="left", padx=(6,0))
        ttk.Button(bar, text="Summary \tCtrl+M", command=self.open_summary).pack(side="left", padx=(6,0))
        paned = ttk.Panedwindow(root, orient="vertical"); paned.grid(row=1, column=0, sticky=N+S+E+W)
        table_frame = ttk.Frame(paned); table_frame.grid_columnconfigure(0, weight=1); table_frame.grid_rowconfigure(0, weight=1)
        cols = ("CfgKey","Type","Key","Old","New"); self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols: self.tree.heading(c, text=c); self.tree.column(c, width=CONFIG.col_widths.get(c, 200), anchor="w")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky=N+S+E+W); vsb.grid(row=0, column=1, sticky=N+S); paned.add(table_frame, weight=1)
        json_frame = ttk.Frame(paned); json_frame.grid_columnconfigure(0, weight=1); json_frame.grid_columnconfigure(2, weight=1); json_frame.grid_rowconfigure(1, weight=1)
        ttk.Label(json_frame, text="OLD").grid(row=0, column=0); ttk.Label(json_frame, text="CURRENT").grid(row=0, column=2)
        self.old_inline = Text(json_frame, height=6, wrap="word", font=CONFIG.font_mono); self.new_inline = Text(json_frame, height=6, wrap="word", font=CONFIG.font_mono)
        self.old_inline.grid(row=1, column=0, sticky=E+W, padx=(0,4)); self.new_inline.grid(row=1, column=2, sticky=E+W, padx=(4,0))
        self.old_full = Text(json_frame, wrap="none", font=CONFIG.font_mono); self.new_full = Text(json_frame, wrap="none", font=CONFIG.font_mono)
        vsb_l = ttk.Scrollbar(json_frame, orient="vertical"); vsb_r = ttk.Scrollbar(json_frame, orient="vertical")
        self.old_full.grid(row=2, column=0, sticky=N+S+E+W); self.new_full.grid(row=2, column=2, sticky=N+S+E+W); vsb_l.grid(row=2, column=1, sticky=N+S); vsb_r.grid(row=2, column=3, sticky=N+S)
        self._synced = SyncedTextPair(self.old_full, self.new_full, vsb_l, vsb_r); paned.add(json_frame, weight=1); self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)

    def _bind_keys(self) -> None:
        self.bind_all("<Control-o>", lambda e: self.open_file()); self.bind_all("<F5>", lambda e: self.compare_now()); self.bind_all("<Control-m>", lambda e: self.open_summary())

    def _initial_dir(self) -> str:
        path = str(self.settings.get("default_open_dir", ""))
        if not path: return os.getcwd()
        if path.startswith("http://") or path.startswith("https://"): unc = sharepoint_url_to_unc(path) or ""; return unc if (unc and os.path.isdir(unc)) else os.getcwd()
        return path if os.path.isdir(path) else os.getcwd()

    def _columns_signature(self, headers: list[str]) -> str:
        canon = [re.sub(r"[^a-z0-9_]", "", h.lower()) for h in headers]
        return "|".join(canon)

    def _maybe_prompt_for_columns(self, headers: list[str]) -> dict[str, str | None]:
        # Try saved mapping first
        sig = self._columns_signature(headers)
        saved = (self.settings.get("column_map", {}) or {}).get(sig)
        pre: dict[str, Optional[str]] | None = saved
        # Try auto-detect as prefill
        df = self.loaded.df if (self.loaded and self.loaded.df is not None) else None
        if df is not None and (not pre):
            pre = self.loader.detect_best_columns(df)
        dlg = ColumnMappingDialog(self, headers, pre)
        self.wait_window(dlg)
        if dlg.result is None:
            raise RuntimeError("Column selection cancelled.")
        # Persist mapping
        maps = self.settings.get("column_map", {}) or {}
        maps[sig] = dlg.result
        self.settings.set("column_map", maps)
        return dlg.result

    def open_file(self) -> None:
        import tkinter.filedialog as fd
        initialdir = self._initial_dir()
        path = fd.askopenfilename(parent=self, initialdir=initialdir,
                                  filetypes=[("Data files", ".csv .tsv .txt .xlsx"),("CSV", ".csv"),("TSV", ".tsv"),("Text", ".txt"),("Excel", ".xlsx")])
        if not path: return
        ok, err = self.loader.validate_file(path)
        if not ok: messagebox.showerror("Open", err); return
        prog = ProgressDialog(self, "Loading…")
        q: queue.Queue[LoadedData | Exception] = queue.Queue()
        def progress_cb(pct: float, msg: str) -> None: self.after(0, lambda: prog.update_status(pct, msg))
        def run() -> None:
            try:
                if path.lower().endswith((".csv",".tsv",".txt")): headers, rows = self.loader.load_csv(path, progress_cb)
                else: headers, rows = self.loader.load_excel(path, None, progress_cb)
                df = self.loader._to_df_from_rows(headers, rows); q.put(LoadedData(headers, rows, df))
            except Exception as exc: q.put(exc)
        threading.Thread(target=run, daemon=True).start()
        def poll() -> None:
            if prog._cancelled: messagebox.showinfo("Loading", "Cancel requested. The operation may complete in the background."); prog.destroy(); return
            try: item = q.get_nowait()
            except queue.Empty: self.after(100, poll); return
            prog.destroy()
            if isinstance(item, Exception): messagebox.showerror("Open", str(item)); return
            self.loaded = item; self._column_map = None
            messagebox.showinfo("Open", f"Loaded {len(item.rows)} rows, {len(item.headers)} columns.")
        poll()

    def compare_now(self) -> None:
        if not self.loaded: messagebox.showwarning("Compare", "Load a file first."); return
        headers, rows = self.loaded.headers, self.loaded.rows
        if not rows: messagebox.showwarning("Compare", "No data rows found."); return

        # Column mapping (auto or prompt once per header signature)
        if self._column_map is None:
            try:
                self._column_map = self._maybe_prompt_for_columns(headers)
            except Exception as exc:
                messagebox.showwarning("Columns", str(exc)); return
        col = self._column_map

        def idx_of(name: Optional[str]) -> Optional[int]:
            if name is None: return None
            try: return headers.index(name)
            except ValueError: return None

        old_idx = idx_of(col.get("payload_old")); new_idx = idx_of(col.get("payload_current"))
        name_idx = idx_of(col.get("config_name_col")); key_idx = idx_of(col.get("config_key_col"))

        if old_idx is None or new_idx is None:
            messagebox.showerror("Compare", "Please select OLD and CURRENT payload columns."); return

        # Use first non-empty row
        target_row = None
        for r in rows:
            if str(r[old_idx] or "").strip() or str(r[new_idx] or "").strip():
                target_row = r; break
        if target_row is None: messagebox.showwarning("Compare", "No rows contain payloads."); return

        old_text = str(target_row[old_idx]) if target_row[old_idx] is not None else ""
        new_text = str(target_row[new_idx]) if target_row[new_idx] is not None else ""
        cfg_display = "-"
        try:
            name_val = str(target_row[name_idx]) if (name_idx is not None and target_row[name_idx] is not None) else ""
            key_val  = str(target_row[key_idx]) if (key_idx  is not None and target_row[key_idx]  is not None) else ""
            cfg_display = key_val or name_val or "-"
        except Exception: pass

        old_obj, _ = try_parse_json(old_text); new_obj, _ = try_parse_json(new_text)
        self.old_json = old_obj if old_obj is not None else old_text
        self.new_json = new_obj if new_obj is not None else new_text

        for w in (self.old_inline, self.new_inline, self.old_full, self.new_full): w.delete("1.0", END)
        self.old_inline.insert(END, json_to_pretty_text(self.old_json)); self.new_inline.insert(END, json_to_pretty_text(self.new_json))
        self.old_full.insert(END, json_to_pretty_text(self.old_json)); self.new_full.insert(END, json_to_pretty_text(self.new_json))

        try: self.diff_dict = run_deepdiff(self.old_json, self.new_json, ignore_order=True, coerce_numeric=True)
        except Exception as exc: messagebox.showerror("DeepDiff", str(exc)); return

        self.tree.delete(*self.tree.get_children())

        def add_row(cfg_key: str, typ: str, key: str, old: Any, new: Any, tag: str) -> None:
            def annotate(x: Any) -> str:
                t = type(x).__name__; return f"{stringify_for_diff(x)} ({t})"
            self.tree.insert("", "end", values=(cfg_key, typ, key, annotate(old), annotate(new)), tags=(tag,))

        def _value_at_path(obj: Any, path: str):
            try:
                cur = obj
                for key, idx in re.findall(r"\['([^']+)'\]|\[(\d+)\]", path):
                    if key:
                        if isinstance(cur, dict): cur = cur.get(key, None)
                        else: return None
                    else:
                        i = int(idx)
                        if isinstance(cur, (list, tuple)) and -len(cur) <= i < len(cur): cur = cur[i]
                        else: return None
                return cur
            except Exception: return None

        dd = self.diff_dict or {}
        for path, change in (dd.get("values_changed", {}) or {}).items(): add_row(cfg_display, "changed", path, change.get("old_value"), change.get("new_value"), "changed")
        for path, change in (dd.get("type_changes", {}) or {}).items(): add_row(cfg_display, "type_changed", path, change.get("old_value"), change.get("new_value"), "changed")
        for path in (dd.get("dictionary_item_added", set()) or set()): add_row(cfg_display, "added", path, "", _value_at_path(self.new_json, path), "added")
        for path in (dd.get("dictionary_item_removed", set()) or set()): add_row(cfg_display, "removed", path, _value_at_path(self.old_json, path), "", "removed")
        iter_added = dd.get("iterable_item_added", {}) or {}
        if isinstance(iter_added, dict):
            for path, new_v in iter_added.items(): add_row(cfg_display, "added", path, "", new_v, "added")
        iter_removed = dd.get("iterable_item_removed", {}) or {}
        if isinstance(iter_removed, dict):
            for path, old_v in iter_removed.items(): add_row(cfg_display, "removed", path, old_v, "", "removed")

        self.tree.tag_configure("changed", background=CONFIG.bg_changed); self.tree.tag_configure("added", background=CONFIG.bg_added); self.tree.tag_configure("removed", background=CONFIG.bg_removed)
        messagebox.showinfo("Compare", "Diff computed. Select a row to highlight in JSON panes.")

    def _on_row_selected(self, event=None) -> None:
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0]); key = str(item["values"][2]); key_regex = escape_path_for_regex(key)
        new_val = item["values"][4]
        try:
            hint_raw = str(new_val).split(" (", 1)[0]; hint = json.dumps(json.loads(hint_raw))
        except Exception: hint = str(new_val).split(" (", 1)[0]
        for txt in (self.old_full, self.new_full): txt.tag_remove("hit", "1.0", END)
        old_text = self.old_full.get("1.0", END); new_text = self.new_full.get("1.0", END)
        for txt, full in ((self.old_full, old_text), (self.new_full, new_text)):
            line = find_line_index(full, key_regex, hint)
            if line:
                index1 = f"{line}.0"; index2 = f"{line}.end"; txt.see(index1); txt.tag_add("hit", index1, index2); txt.tag_config("hit", background=CONFIG.json_hit_bg, foreground=CONFIG.json_hit_fg)

    def _set_default_folder(self) -> None:
        import tkinter.filedialog as fd
        path = fd.askdirectory(title="Set Default Folder", mustexist=True); if not path: return
        self.settings.set("default_open_dir", path); messagebox.showinfo("Settings", f"Default folder set to:\n{path}")
    def _set_default_from_sp(self) -> None:
        from tkinter.simpledialog import askstring
        url = askstring("Default from SharePoint URL", "Enter SharePoint/OneDrive URL:"); if not url: return
        unc = sharepoint_url_to_unc(url)
        if unc and os.path.isdir(unc):
            self.settings.set("default_open_dir", unc); messagebox.showinfo("Settings", f"Default folder set to mapped path:\n{unc}")
        else:
            messagebox.showwarning("Settings", "The URL could not be mapped to an accessible folder. Saved URL anyway."); self.settings.set("default_open_dir", url)
    def open_summary(self) -> None:
        df = self.loaded.df if (self.loaded and self.loaded.df is not None) else None; SummaryDashboard(self, df)
def main() -> None:
    app = App(); app.mainloop()
