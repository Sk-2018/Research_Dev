# -*- coding: utf-8 -*-
"""
payload_wizard_v121.py

Tkinter wizard for running SELECT-only queries against Postgres and exporting to Excel.
- Regions/Environments/Hosts prefilled from HOSTMAP.
- Query UI supports Default template or Custom SQL.
- SELECT-only enforcement with auto-fix (fill {schema}, trim to first SELECT, remove trailing ';').
- Uses COPY-to-CSV by default to avoid datetime overflow issues (year 10000/infinity).
- Read-only session, timeouts, retry on "too many connections".
- Audit CSV written to output folder after every run.
- Optional: open Test103.py (PayloadDiffViewer) with --open <file> after export.
Windows-friendly. Auto-detects psycopg v3 or psycopg2.
"""

import os
import re
import sys
import csv
import hashlib
import time
import tempfile
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_VERSION = "1.2.1"
AUDIT_BASENAME = "payload_wizard_audit.csv"

# Detect psycopg driver
HAVE_PG3 = False
HAVE_PG2 = False
psycopg3 = None
psycopg2 = None
try:
    import psycopg as psycopg3  # psycopg v3
    HAVE_PG3 = True
except Exception:
    pass
if not HAVE_PG3:
    try:
        import psycopg2  # psycopg2
        HAVE_PG2 = True
    except Exception:
        pass

import pandas as pd

# Utilities list
UTILS = ["Payload Comparison", "XYZ", "ABC"]

# Estate mapping (Region x Env)
HOSTMAP = {
    # SA-Central
    ("SA-Central", "MTF"):  {"hosts": ["ljnb5cdb7466", "lgg5cdb7083", "lqra5cdb7600"], "port": 6432, "dbname": "pgdb_msdc1",  "schema": "sdc_owner"},
    ("SA-Central", "PROD"): {"hosts": ["ljnb5cdb753",  "lqra5cdb8013", "lqra5cdb7706"], "port": 6432, "dbname": "pgdb_padc1",  "schema": "sdc_owner"},

    # US Central
    ("US Central", "MTF"):  {"hosts": ["lkc2cdb7525", "lmk2cdb7489", "lkc2cdb7686"], "port": 6432, "dbname": "pgdb_pawd001", "schema": "sdc_owner"},
    ("US Central", "PROD"): {"hosts": ["lkc2cdb7525", "lmk2cdb7489", "lkc2cdb7686"], "port": 6432, "dbname": "pgdb_pawd001", "schema": "sdc_owner"},

    # MTF (Global)
    ("MTF (Global)", "MTF"):  {"hosts": ["lstl5cdb7301", "lstl5cdb7357", "lstl5cdb7188"], "port": 6432, "dbname": "pgdb_msdc001", "schema": "sdc_owner"},
    ("MTF (Global)", "PROD"): {"hosts": ["lstl5cdb7301", "lstl5cdb7357", "lstl5cdb7188"], "port": 6432, "dbname": "pgdb_msdc001", "schema": "sdc_owner"},

    # SDC-STL (Global)
    ("SDC-STL (Global)", "MTF"):  {"hosts": ["lstl2cdb5798", "lstl2cdb4369", "lstl2cdb5380"], "port": 6432, "dbname": "pgdb_pawd002", "schema": "swd_owner"},
    ("SDC-STL (Global)", "PROD"): {"hosts": ["lstl2cdb5798", "lstl2cdb4369", "lstl2cdb5380"], "port": 6432, "dbname": "pgdb_pawd002", "schema": "swd_owner"},

    # SDC-KSC (Global)
    ("SDC-KSC (Global)", "MTF"):  {"hosts": ["lkc2cdb5172", "lkc2cdb5163", "lkc2cdb5284"], "port": 6432, "dbname": "pgdb_pawd003", "schema": "swd_owner"},
    ("SDC-KSC (Global)", "PROD"): {"hosts": ["lkc2cdb5172", "lkc2cdb5163", "lkc2cdb5284"], "port": 6432, "dbname": "pgdb_pawd003", "schema": "swd_owner"},
}

REGIONS = sorted({r for (r, _e) in HOSTMAP.keys()})
ENVS    = sorted({e for (_r, e) in HOSTMAP.keys()})

DEFAULT_OUTDIR = os.path.expanduser("~")

# Default SQL template (no trailing semicolon; schema placeholder)
DEFAULT_SQL_PAYLOAD_TEMPLATE = (
    "WITH base AS (\n"
    "    SELECT\n"
    "        a.acq_profl_upstream_id AS config_key,\n"
    "        a.pyld                   AS current_payload,\n"
    "        b.pyld                   AS old_payload,\n"
    "        a.config_eff_ts::text    AS config_eff_ts,\n"
    "        a.param_exp_ts::text     AS param_exp_ts,\n"
    "        a.rec_sts                AS rec_sts\n"
    "    FROM {schema}.acq_profl a\n"
    "    LEFT JOIN {schema}.acq_profl b\n"
    "      ON a.acq_profl_upstream_id = b.acq_profl_upstream_id\n"
    "     AND a.config_eff_ts = b.param_exp_ts - INTERVAL '12 hours'\n"
    "    WHERE a.config_eff_ts >= TIMEZONE('UTC', NOW()) - INTERVAL '24 hours'\n"
    ")\n"
    "SELECT\n"
    "    'acq_profl'           AS \"Config Name\",\n"
    "    config_key            AS \"Config Key\",\n"
    "    current_payload       AS \"CURRENT PAYLOAD\",\n"
    "    old_payload           AS \"OLD PAYLOAD\",\n"
    "    config_eff_ts,\n"
    "    param_exp_ts,\n"
    "    rec_sts\n"
    "FROM base\n"
    "ORDER BY config_eff_ts DESC\n"
    "LIMIT 5000"
)

# Helpers
def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    cleaned = []
    for line in sql.splitlines():
        if "--" in line:
            line = line.split("--", 1)[0]
        cleaned.append(line)
    return "\n".join(cleaned)

def looks_like_select_only(sql: str) -> bool:
    s = _strip_comments(sql).strip()
    if not s:
        return False
    parts = [p for p in s.split(";") if p.strip()]
    if len(parts) > 1:
        return False
    s0 = parts[0].lstrip().lower()
    return s0.startswith("select") or s0.startswith("with")

def auto_fix_sql(sql: str, schema: str):
    notes = []
    original = sql

    if "{schema}" in sql:
        sql = sql.replace("{schema}", schema)
        notes.append("filled {schema} -> %s" % schema)

    if schema and schema != "sdc_owner":
        new_sql = re.sub(r"\bsdc_owner\.", f"{schema}.", sql)
        if new_sql != sql:
            sql = new_sql
            notes.append("rewrote sdc_owner.* -> %s.*" % schema)

    stripped = _strip_comments(sql)
    parts = [p for p in stripped.split(";") if p.strip()]
    if len(parts) > 1:
        sql = parts[0].strip()
        notes.append("removed extra statements after first semicolon")
    else:
        sql = parts[0].strip()
        if original.strip().endswith(";"):
            notes.append("removed trailing semicolon")

    low = sql.lower()
    if not (low.startswith("select") or low.startswith("with")):
        m = re.search(r"\b(with|select)\b", low)
        if m:
            start = m.start()
            sql = sql[start:].strip()
            notes.append("trimmed leading non-SELECT content")

    if re.search(r"\blimit\b", low) is None:
        notes.append("no LIMIT detected (COPY mode recommended)")

    return sql, notes

def sanitize_sql_for_log(sql: str, max_len: int = 2000) -> str:
    s = " ".join(sql.split())
    if len(s) > max_len:
        s = s[:max_len] + " ...(truncated)..."
    return s

def connect_pg(cfg: dict, user: str, pwd: str, attempts: int = 4):
    host = cfg["host"]; port = int(cfg["port"]); dbname = cfg["dbname"]
    options = "-c statement_timeout=120000 -c idle_in_transaction_session_timeout=60000"
    last = None
    for i in range(attempts):
        try:
            if HAVE_PG3:
                conn = psycopg3.connect(host=host, port=port, dbname=dbname, user=user, password=pwd,
                                        connect_timeout=8, options=options)
            elif HAVE_PG2:
                conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=pwd,
                                        connect_timeout=8, options=options)
            else:
                raise ImportError("Install psycopg[binary] or psycopg2")
            cur = conn.cursor()
            try:
                cur.execute("SET application_name='payload_wizard'")
                cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
            return conn
        except Exception as e:
            last = e
            msg = str(e).lower()
            if "too many connections" in msg or "remaining connection slots" in msg:
                time.sleep([3, 6, 10, 15][min(i, 3)])
                continue
            raise
    raise last

def write_audit(outdir: str, row: dict) -> str:
    audit_path = os.path.join(outdir or DEFAULT_OUTDIR, AUDIT_BASENAME)
    exists = os.path.exists(audit_path)
    fieldnames = [
        "timestamp","result","error","duration_ms",
        "region","environment","host","port","dbname","schema",
        "user","driver","mode","rows","outfile","query_sha256","query"
    ]
    with open(audit_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)
    return audit_path

# UI Frames
class ParentScreen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        pad = {"padx": 10, "pady": 8}

        ttk.Label(self, text="REGION").grid(row=0, column=0, sticky="w", **pad)
        self.cb_region = ttk.Combobox(self, values=REGIONS, state="readonly")
        self.cb_region.grid(row=0, column=1, sticky="we", **pad)

        ttk.Label(self, text="Environment").grid(row=0, column=2, sticky="w", **pad)
        self.cb_env = ttk.Combobox(self, values=ENVS, state="readonly")
        self.cb_env.grid(row=0, column=3, sticky="we", **pad)

        ttk.Label(self, text="Utility Run").grid(row=1, column=0, sticky="w", **pad)
        self.cb_util = ttk.Combobox(self, values=UTILS, state="readonly", width=28)
        self.cb_util.grid(row=1, column=1, sticky="we", **pad)

        self.btn_next = ttk.Button(self, text="Next ▶", command=self.on_next)
        self.btn_next.grid(row=2, column=3, sticky="e", **pad)

        for c in range(4):
            self.columnconfigure(c, weight=1)

    def on_next(self):
        region = self.cb_region.get().strip()
        env    = self.cb_env.get().strip()
        util   = self.cb_util.get().strip()
        if not (region and env and util):
            messagebox.showerror("Choose all fields", "Select Region, Environment, and Utility")
            return
        cfg = HOSTMAP.get((region, env))
        if not cfg:
            messagebox.showerror("No host mapping", "Add HOSTMAP entry in code")
            return
        self.app.selection = {"region": region, "env": env, "util": util, "cfg": cfg}
        self.app.show_creds()

class CredsScreen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        pad = {"padx": 10, "pady": 8}

        self.var_host = tk.StringVar()
        self.var_port = tk.StringVar()
        self.var_db = tk.StringVar()

        ttk.Label(self, text="Host").grid(row=0, column=0, sticky="w", **pad)
        self.cb_host = ttk.Combobox(self, textvariable=self.var_host, values=[], state="readonly", width=42)
        self.cb_host.grid(row=0, column=1, sticky="we", **pad)

        ttk.Label(self, text="Port").grid(row=0, column=2, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.var_port, width=10).grid(row=0, column=3, sticky="w", **pad)

        ttk.Label(self, text="DB").grid(row=0, column=4, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.var_db, width=18).grid(row=0, column=5, sticky="w", **pad)

        ttk.Label(self, text="User").grid(row=1, column=0, sticky="w", **pad)
        self.e_user = ttk.Entry(self, width=26)
        self.e_user.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(self, text="Password").grid(row=1, column=2, sticky="w", **pad)
        self.e_pwd = ttk.Entry(self, width=26, show="*")
        self.e_pwd.grid(row=1, column=3, sticky="w", **pad)

        ttk.Label(self, text="Output folder").grid(row=1, column=4, sticky="w", **pad)
        self.e_out = ttk.Entry(self, width=28)
        self.e_out.insert(0, DEFAULT_OUTDIR)
        self.e_out.grid(row=1, column=5, sticky="we", **pad)
        ttk.Button(self, text="Browse…", command=self.on_browse).grid(row=1, column=6, sticky="w", **pad)

        self.btn_back = ttk.Button(self, text="◀ Back", command=self.app.show_parent)
        self.btn_back.grid(row=2, column=0, sticky="w", **pad)
        self.btn_next = ttk.Button(self, text="Next ▶", command=self.on_next)
        self.btn_next.grid(row=2, column=6, sticky="e", **pad)

        for c in range(7):
            self.columnconfigure(c, weight=1)

    def on_browse(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.e_out.delete(0, tk.END)
            self.e_out.insert(0, d)

    def load_from_selection(self):
        cfg = self.app.selection["cfg"]
        hosts = cfg.get("hosts")
        if hosts:
            self.cb_host["values"] = list(hosts)
            self.var_host.set(hosts[0])
        else:
            self.cb_host["values"] = [cfg.get("host", "")]
            self.var_host.set(cfg.get("host", ""))
        self.var_port.set(str(cfg.get("port", 6432)))
        self.var_db.set(cfg.get("dbname", "sdc"))

    def on_next(self):
        host = self.var_host.get().strip()
        port = self.var_port.get().strip()
        db   = self.var_db.get().strip()
        user = self.e_user.get().strip()
        pwd  = self.e_pwd.get().strip()
        outdir = self.e_out.get().strip()
        if not (host and port and db and user and pwd and outdir):
            messagebox.showerror("Missing input", "Fill all fields and choose an output folder")
            return
        if not os.path.isdir(outdir):
            messagebox.showerror("Output folder", "Choose a valid directory")
            return
        cfg = dict(self.app.selection["cfg"])
        cfg["host"] = host
        self.app.selection.update({"host": host, "port": port, "db": db, "user": user, "pwd": pwd, "outdir": outdir, "cfg": cfg})
        self.app.show_utility()

class UtilityScreen(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.inner = None
        pad = {"padx": 10, "pady": 8}
        ttk.Label(self, text="Utility:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Button(self, text="◀ Back", command=self.app.show_creds).grid(row=0, column=1, sticky="e", **pad)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def load_utility(self):
        if self.inner is not None:
            self.inner.destroy()
            self.inner = None
        util = self.app.selection.get("util")
        if util == "Payload Comparison":
            self.inner = PayloadComparisonFrame(self, self.app)
            schema = self.app.selection.get("cfg", {}).get("schema", "sdc_owner")
            self.inner.load_defaults_from_selection(schema)
        elif util == "XYZ":
            self.inner = PlaceholderFrame(self, text="XYZ utility – coming soon")
        else:
            self.inner = PlaceholderFrame(self, text="ABC utility – coming soon")
        self.inner.grid(row=1, column=0, columnspan=2, sticky="nsew")

class PlaceholderFrame(ttk.Frame):
    def __init__(self, master, text: str):
        super().__init__(master)
        ttk.Label(self, text=text).pack(padx=12, pady=12)

class PayloadComparisonFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.running = False
        pad = {"padx": 10, "pady": 6}

        drv = "psycopg (v3)" if HAVE_PG3 else ("psycopg2" if HAVE_PG2 else "none")
        ttk.Label(self, text=f"Driver detected: {drv} | OS: {'Windows' if os.name=='nt' else os.name}").grid(row=0, column=0, columnspan=8, sticky="w", **pad)

        self.var_mode = tk.StringVar(value="default")
        ttk.Label(self, text="Query Mode").grid(row=1, column=0, sticky="w", **pad)
        ttk.Radiobutton(self, text="Use Default Template", variable=self.var_mode, value="default").grid(row=1, column=1, sticky="w", **pad)
        ttk.Radiobutton(self, text="Use Custom SQL",      variable=self.var_mode, value="custom").grid(row=1, column=2, sticky="w", **pad)

        ttk.Label(self, text="SQL (SELECT only)").grid(row=2, column=0, sticky="w", **pad)
        self.txt_sql = tk.Text(self, height=14, wrap="word")
        self.txt_sql.grid(row=3, column=0, columnspan=8, sticky="nsew", **pad)
        self.rowconfigure(3, weight=1)
        for c in range(8):
            self.columnconfigure(c, weight=1)

        self.var_copy = tk.IntVar(value=1)
        ttk.Checkbutton(self, text="Use COPY mode (keeps timestamps as text)", variable=self.var_copy).grid(row=4, column=0, sticky="w", **pad)

        self.var_autofix = tk.IntVar(value=1)
        ttk.Checkbutton(self, text="Auto-fix SQL (fill schema, trim to first SELECT, remove trailing ;)", variable=self.var_autofix).grid(row=4, column=1, sticky="w", **pad)

        self.var_open = tk.IntVar(value=0)
        ttk.Checkbutton(self, text="Open in PayloadDiffViewer (Test103.py) after export", variable=self.var_open).grid(row=4, column=2, sticky="w", **pad)
        self.e_viewer = ttk.Entry(self, width=40)
        self.e_viewer.insert(0, os.environ.get("PAYLOAD_DIFFVIEWER_PATH", ""))
        self.e_viewer.grid(row=4, column=3, columnspan=3, sticky="we", **pad)
        ttk.Button(self, text="Find Viewer…", command=self.on_pick_viewer).grid(row=4, column=6, sticky="e", **pad)

        ttk.Button(self, text="Load SQL…", command=self.on_load_sql).grid(row=5, column=0, sticky="w", **pad)
        ttk.Button(self, text="Save SQL…", command=self.on_save_sql).grid(row=5, column=1, sticky="w", **pad)
        ttk.Button(self, text="Reset to Default", command=self.on_reset_default).grid(row=5, column=2, sticky="w", **pad)

        self.btn_run = ttk.Button(self, text="Run → Export Excel", command=self.on_run)
        self.btn_run.grid(row=5, column=6, sticky="e", **pad)
        self.pb = ttk.Progressbar(self, mode="indeterminate")
        self.pb.grid(row=5, column=3, columnspan=3, sticky="we", **pad)

        ttk.Label(self, text="Log").grid(row=6, column=0, sticky="w", **pad)
        self.txt_log = tk.Text(self, height=8)
        self.txt_log.grid(row=7, column=0, columnspan=8, sticky="nsew", **pad)
        self.rowconfigure(7, weight=1)

        self.lbl_audit = ttk.Label(self, text="Audit: (will be created in your output folder)")
        self.lbl_audit.grid(row=8, column=0, columnspan=8, sticky="w", **pad)

    def load_defaults_from_selection(self, schema: str):
        self.txt_sql.delete("1.0", tk.END)
        self.txt_sql.insert("1.0", DEFAULT_SQL_PAYLOAD_TEMPLATE.format(schema=schema))

    def on_pick_viewer(self):
        p = filedialog.askopenfilename(title="Select Test103.py (PayloadDiffViewer)", filetypes=[("Python", "*.py"), ("All", "*.*")])
        if p:
            self.e_viewer.delete(0, tk.END)
            self.e_viewer.insert(0, p)

    def on_load_sql(self):
        p = filedialog.askopenfilename(title="Load SQL", filetypes=[("SQL", "*.sql"), ("Text", "*.txt"), ("All", "*.*")])
        if not p:
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = f.read()
            self.txt_sql.delete("1.0", tk.END)
            self.txt_sql.insert("1.0", data)
            self.log(f"Loaded SQL from: {p}")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))

    def on_save_sql(self):
        p = filedialog.asksaveasfilename(title="Save SQL", defaultextension=".sql", filetypes=[("SQL", "*.sql"), ("Text", "*.txt")])
        if not p:
            return
        try:
            data = self.txt_sql.get("1.0", tk.END)
            with open(p, "w", encoding="utf-8") as f:
                f.write(data)
            self.log(f"Saved SQL to: {p}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def on_reset_default(self):
        schema = self.app.selection.get("cfg", {}).get("schema", "sdc_owner")
        self.load_defaults_from_selection(schema)
        self.var_mode.set("default")
        self.log("Reset SQL to default template.")

    # Logging helpers
    def log(self, msg: str):
        self.after(0, self._append, msg)

    def _append(self, msg: str):
        self.txt_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.txt_log.see(tk.END)

    def set_running(self, on: bool):
        self.running = on
        if on:
            self.btn_run.configure(state=tk.DISABLED)
            self.pb.start(70)
        else:
            self.btn_run.configure(state=tk.NORMAL)
            self.pb.stop()

    def on_run(self):
        if self.running:
            return
        mode = self.var_mode.get()
        schema = self.app.selection.get("cfg", {}).get("schema", "sdc_owner")

        if mode == "default":
            sql = DEFAULT_SQL_PAYLOAD_TEMPLATE.format(schema=schema)
        else:
            sql = self.txt_sql.get("1.0", tk.END)

        if mode == "custom" and bool(self.var_autofix.get()):
            fixed, notes = auto_fix_sql(sql, schema)
            if fixed != sql:
                self.txt_sql.delete("1.0", tk.END)
                self.txt_sql.insert("1.0", fixed)
                for n in notes:
                    self.log("auto-fix: " + n)
            sql = fixed

        if not looks_like_select_only(sql):
            messagebox.showerror("Only SELECT allowed", "Provide a single SELECT (or WITH ... SELECT) statement.")
            return

        sel = self.app.selection
        cfg = {"host": sel["host"], "port": sel["port"], "dbname": sel["db"], "schema": schema}
        user, pwd, outdir = sel["user"], sel["pwd"], sel["outdir"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        outfile = os.path.join(outdir, f"payload_export_{ts}.xlsx")
        open_viewer = bool(self.var_open.get())
        viewer_path = self.e_viewer.get().strip()
        use_copy = bool(self.var_copy.get())

        self.set_running(True)
        t = threading.Thread(target=self.worker, args=(cfg, user, pwd, sql.strip(), outfile, use_copy, open_viewer, viewer_path, outdir), daemon=True)
        t.start()

    def worker(self, cfg, user, pwd, sql, outfile, use_copy, open_viewer, viewer_path, outdir):
        start = time.perf_counter()
        conn = None
        tmp_csv = None
        result = "SUCCESS"
        err_msg = ""
        row_count = 0
        try:
            self.log("Connecting...")
            conn = connect_pg(cfg, user, pwd)
            self.log("Connected (read-only, timeouts set).")

            if use_copy:
                self.log("Using COPY -> CSV stream")
                copy_sql = f"COPY ({sql}) TO STDOUT WITH CSV HEADER"
                fd, tmp_csv = tempfile.mkstemp(prefix="pg_export_", suffix=".csv")
                os.close(fd)
                cur = conn.cursor()
                try:
                    if HAVE_PG3:
                        with open(tmp_csv, "wb") as f:
                            with cur.copy(copy_sql) as cp:
                                while True:
                                    chunk = cp.read()
                                    if not chunk:
                                        break
                                    f.write(chunk)
                    else:
                        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
                            cur.copy_expert(copy_sql, f)
                finally:
                    try:
                        cur.close()
                    except Exception:
                        pass
                df = pd.read_csv(tmp_csv)
            else:
                self.log("Cursor fetch path")
                cur = conn.cursor()
                try:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    cols = []
                    for d in cur.description:
                        name = getattr(d, "name", None)
                        if name is None and isinstance(d, (tuple, list)) and len(d) > 0:
                            name = d[0]
                        if name is None:
                            name = "col"
                        cols.append(str(name))
                finally:
                    try:
                        cur.close()
                    except Exception:
                        pass
                df = pd.DataFrame(rows, columns=cols)

            row_count = len(df)
            if row_count == 0:
                self.log("No rows returned.")
                self.after(0, messagebox.showinfo, "No data", "Query returned 0 rows.")
                result = "SUCCESS"
                return

            meta = pd.DataFrame(
                [
                    ("app_version", APP_VERSION),
                    ("os", "Windows" if os.name == "nt" else os.name),
                    ("driver", "psycopg (v3)" if HAVE_PG3 else ("psycopg2" if HAVE_PG2 else "none")),
                    ("db_host", cfg["host"]),
                    ("db_name", cfg["dbname"]),
                    ("row_count", row_count),
                    ("generated_at", datetime.now().isoformat(timespec="seconds")),
                    ("mode", "COPY" if use_copy else "cursor"),
                ],
                columns=["key", "value"]
            )
            with pd.ExcelWriter(outfile, engine="openpyxl") as xw:
                df.to_excel(xw, index=False, sheet_name="data")
                meta.to_excel(xw, index=False, sheet_name="metadata")
            self.log(f"Exported: {outfile}")

            if open_viewer:
                self.log("Launching PayloadDiffViewer...")
                if not viewer_path or not os.path.isfile(viewer_path):
                    self.log("Viewer path invalid; skipping open.")
                else:
                    import subprocess
                    try:
                        subprocess.Popen([sys.executable, viewer_path, "--open", outfile])
                    except Exception as e:
                        self.log("Launch warning: " + str(e))

            self.after(0, messagebox.showinfo, "Done", f"Excel written:\n{outfile}")
        except Exception as e:
            result = "ERROR"
            err_msg = str(e)
            self.log("ERROR: " + err_msg)
            if "too many connections" in err_msg.lower():
                self.after(0, messagebox.showerror, "Connection pool full", "Too many connections for your role. Close idle sessions or retry later.")
            else:
                self.after(0, messagebox.showerror, "Run failed", err_msg)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(0.05)
            if tmp_csv and os.path.exists(tmp_csv):
                try:
                    os.remove(tmp_csv)
                except Exception:
                    pass

            duration_ms = int((time.perf_counter() - start) * 1000)
            driver = "psycopg (v3)" if HAVE_PG3 else ("psycopg2" if HAVE_PG2 else "none")
            sql_log = sanitize_sql_for_log(sql)
            qhash = hashlib.sha256(sql_log.encode("utf-8", errors="ignore")).hexdigest()
            audit_row = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "result": result,
                "error": err_msg,
                "duration_ms": duration_ms,
                "region": self.app.selection.get("region"),
                "environment": self.app.selection.get("env"),
                "host": cfg.get("host"),
                "port": self.app.selection.get("port"),
                "dbname": cfg.get("dbname"),
                "schema": cfg.get("schema"),
                "user": self.app.selection.get("user"),
                "driver": driver,
                "mode": "COPY" if use_copy else "cursor",
                "rows": row_count,
                "outfile": outfile if result == "SUCCESS" else "",
                "query_sha256": qhash,
                "query": sql_log,
            }
            try:
                audit_path = write_audit(outdir, audit_row)
                self.log(f"Audit written -> {audit_path}")
                self.after(0, self.lbl_audit.configure, {"text": f"Audit: {audit_path}"})
            except Exception as ae:
                self.log("Audit write failed: " + str(ae))
            self.after(0, self.set_running, False)

# App shell
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Payload Wizard (v{APP_VERSION})")
        self.geometry("1180x800")
        self.selection = {}
        self.parent = ParentScreen(self, self)
        self.creds  = CredsScreen(self, self)
        self.util   = UtilityScreen(self, self)
        self.parent.pack(fill=tk.BOTH, expand=True)

    def show_parent(self):
        self.creds.pack_forget()
        self.util.pack_forget()
        self.parent.pack(fill=tk.BOTH, expand=True)

    def show_creds(self):
        self.parent.pack_forget()
        self.util.pack_forget()
        self.creds.pack(fill=tk.BOTH, expand=True)
        self.creds.load_from_selection()

    def show_utility(self):
        self.parent.pack_forget()
        self.creds.pack_forget()
        self.util.pack(fill=tk.BOTH, expand=True)
        self.util.load_utility()

if __name__ == "__main__":
    App().mainloop()
