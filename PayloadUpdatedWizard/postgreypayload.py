
"""
Tkinter GUI: PostgreSQL Export Tool (Windows-friendly)
- Host, Port, DB are hardcoded
- Prompts only for Username & Password (authorization)
- Pre-checks: connectivity + object access
- Runs 'issr_profl' diff query with lookback & limit; exports CSV
- Optional: exports schema/table & column inventory to CSV
"""

import os
import csv
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import psycopg

# ------------------- Hardcoded connection details -------------------
PG_HOST = "ljnb5cdb7466"
PG_PORT = 6432
PG_DBNAME = "pgdb_msdc1"

# ------------------- SQL: Custom issr_profl diff query -------------------
CUSTOM_QUERY = """
SELECT
  'issr_profl' AS "Config Name",
  A.issr_profl_upstream_id AS "Config Key",
  A.pyld AS "CURRENT PAYLOAD",
  B.pyld AS "OLD PAYLOAD",
  A.config_eff_ts,
  A.rec_sts,
  A.param_exp_ts
FROM sdc_owner.issr_profl A
LEFT JOIN sdc_owner.issr_profl B
  ON A.issr_profl_upstream_id = B.issr_profl_upstream_id
 AND A.config_eff_ts = B.param_exp_ts - INTERVAL '12 hours'
WHERE A.config_eff_ts >= TIMEZONE('UTC', NOW() - %s::interval)
ORDER BY A.config_eff_ts DESC, A.issr_profl_upstream_id
LIMIT %s;
"""

EXCLUDED_SCHEMAS = (
    "pg_catalog",
    "information_schema",
    "pg_toast",
    "pg_temp_1",
    "pg_toast_temp_1",
)

# ------------------- Utility functions -------------------
def ts_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def abspath(p):
    try:
        return os.path.abspath(p)
    except Exception:
        return p

def write_csv(path, header, rows):
    # utf-8-sig helps Excel auto-detect UTF8
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

# ------------------- Main App -------------------
class PgExporterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PostgreSQL Export Tool")
        self.geometry("820x640")
        self.minsize(820, 640)

        self.create_widgets()
        self.set_defaults()

    def create_widgets(self):
        pad = {'padx': 8, 'pady': 6}

        # ---- Frame: Connection (hardcoded shown, user/pass prompted) ----
        frm_conn = ttk.LabelFrame(self, text="Connection")
        frm_conn.pack(fill="x", **pad)

        ttk.Label(frm_conn, text="Host:").grid(row=0, column=0, sticky="e")
        self.ent_host = ttk.Entry(frm_conn, width=28)
        self.ent_host.grid(row=0, column=1, sticky="w", padx=4)
        self.ent_host.configure(state="disabled")

        ttk.Label(frm_conn, text="Port:").grid(row=0, column=2, sticky="e")
        self.ent_port = ttk.Entry(frm_conn, width=10)
        self.ent_port.grid(row=0, column=3, sticky="w", padx=4)
        self.ent_port.configure(state="disabled")

        ttk.Label(frm_conn, text="Database:").grid(row=0, column=4, sticky="e")
        self.ent_db = ttk.Entry(frm_conn, width=22)
        self.ent_db.grid(row=0, column=5, sticky="w", padx=4)
        self.ent_db.configure(state="disabled")

        ttk.Label(frm_conn, text="Username:").grid(row=1, column=0, sticky="e")
        self.ent_user = ttk.Entry(frm_conn, width=28)
        self.ent_user.grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(frm_conn, text="Password:").grid(row=1, column=2, sticky="e")
        self.ent_pass = ttk.Entry(frm_conn, width=22, show="*")
        self.ent_pass.grid(row=1, column=3, sticky="w", padx=4)

        self.var_showpass = tk.BooleanVar(value=False)
        chk_show = ttk.Checkbutton(frm_conn, text="Show", variable=self.var_showpass, command=self.toggle_password)
        chk_show.grid(row=1, column=4, sticky="w")

        for c in range(6):
            frm_conn.grid_columnconfigure(c, weight=0)

        # ---- Frame: Query Options ----
        frm_query = ttk.LabelFrame(self, text="Query Options (issr_profl diff)")
        frm_query.pack(fill="x", **pad)

        ttk.Label(frm_query, text="Lookback interval:").grid(row=0, column=0, sticky="e")
        self.ent_lookback = ttk.Entry(frm_query, width=16)
        self.ent_lookback.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(frm_query, text="e.g., 24 hours, 2 days").grid(row=0, column=2, sticky="w")

        ttk.Label(frm_query, text="Row limit:").grid(row=0, column=3, sticky="e")
        self.ent_limit = ttk.Entry(frm_query, width=8)
        self.ent_limit.grid(row=0, column=4, sticky="w", padx=4)

        self.var_open_folder = tk.BooleanVar(value=True)
        chk_open = ttk.Checkbutton(frm_query, text="Open folder after export", variable=self.var_open_folder)
        chk_open.grid(row=0, column=5, sticky="w")

        for c in range(6):
            frm_query.grid_columnconfigure(c, weight=0)

        # ---- Optional: Inventory Export ----
        frm_inv = ttk.LabelFrame(self, text="Optional Inventory Export")
        frm_inv.pack(fill="x", **pad)

        self.var_export_inventory = tk.BooleanVar(value=False)
        chk_inv = ttk.Checkbutton(frm_inv, text="Also export schema/table & column inventory", variable=self.var_export_inventory)
        chk_inv.grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(frm_inv, text="Schema filter (optional):").grid(row=1, column=0, sticky="e")
        self.ent_only_schema = ttk.Entry(frm_inv, width=24)
        self.ent_only_schema.grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(frm_inv, text="Table name LIKE (e.g. %cust%):").grid(row=1, column=2, sticky="e")
        self.ent_table_like = ttk.Entry(frm_inv, width=24)
        self.ent_table_like.grid(row=1, column=3, sticky="w", padx=4)

        for c in range(4):
            frm_inv.grid_columnconfigure(c, weight=0)

        # ---- Frame: Output ----
        frm_out = ttk.LabelFrame(self, text="Output")
        frm_out.pack(fill="x", **pad)

        ttk.Label(frm_out, text="Folder:").grid(row=0, column=0, sticky="e")
        self.ent_folder = ttk.Entry(frm_out)
        self.ent_folder.grid(row=0, column=1, sticky="we", padx=4)
        btn_browse = ttk.Button(frm_out, text="Browse…", command=self.browse_folder)
        btn_browse.grid(row=0, column=2, sticky="w")

        frm_out.grid_columnconfigure(1, weight=1)

        # ---- Frame: Controls ----
        frm_ctrl = ttk.Frame(self)
        frm_ctrl.pack(fill="x", **pad)

        self.btn_run = ttk.Button(frm_ctrl, text="Run Export", command=self.on_run)
        self.btn_run.pack(side="left")

        self.btn_quit = ttk.Button(frm_ctrl, text="Quit", command=self.destroy)
        self.btn_quit.pack(side="left", padx=6)

        self.prg = ttk.Progressbar(frm_ctrl, mode="indeterminate")
        self.prg.pack(fill="x", padx=10, expand=True)

        # ---- Frame: Status Log ----
        frm_log = ttk.LabelFrame(self, text="Status")
        frm_log.pack(fill="both", expand=True, **pad)

        self.txt_log = tk.Text(frm_log, height=18, wrap="word")
        self.txt_log.pack(fill="both", expand=True)

    def set_defaults(self):
        # Set hardcoded values in disabled entries
        self.ent_host.configure(state="normal"); self.ent_host.delete(0, tk.END); self.ent_host.insert(0, PG_HOST); self.ent_host.configure(state="disabled")
        self.ent_port.configure(state="normal"); self.ent_port.delete(0, tk.END); self.ent_port.insert(0, str(PG_PORT)); self.ent_port.configure(state="disabled")
        self.ent_db.configure(state="normal"); self.ent_db.delete(0, tk.END); self.ent_db.insert(0, PG_DBNAME); self.ent_db.configure(state="disabled")

        self.ent_lookback.insert(0, "24 hours")
        self.ent_limit.insert(0, "100")
        self.ent_folder.insert(0, os.getcwd())

    def toggle_password(self):
        self.ent_pass.configure(show="" if self.var_showpass.get() else "*")

    def browse_folder(self):
        d = filedialog.askdirectory(title="Choose output folder", initialdir=self.ent_folder.get() or os.getcwd())
        if d:
            self.ent_folder.delete(0, tk.END)
            self.ent_folder.insert(0, d)

    def log(self, msg):
        self.txt_log.insert(tk.END, f"[{ts_now()}] {msg}\n")
        self.txt_log.see(tk.END)
        self.update_idletasks()

    def set_running(self, running: bool):
        if running:
            self.btn_run.configure(state="disabled")
            self.prg.start(10)
        else:
            self.prg.stop()
            self.btn_run.configure(state="normal")

    def on_run(self):
        user = self.ent_user.get().strip()
        pwd  = self.ent_pass.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Missing credentials", "Please enter username and password.")
            return
        lookback = self.ent_lookback.get().strip() or "24 hours"
        limit_txt = self.ent_limit.get().strip() or "100"
        try:
            limit = int(limit_txt)
            if limit <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("Invalid limit", "Row limit must be a positive integer.")
            return

        outdir = self.ent_folder.get().strip() or os.getcwd()
        if not os.path.isdir(outdir):
            messagebox.showerror("Invalid folder", "Please choose a valid output folder.")
            return
        # Gather optional inventory parameters
        do_inventory = self.var_export_inventory.get()
        only_schema = self.ent_only_schema.get().strip()
        table_like  = self.ent_table_like.get().strip()

        # Run in background thread
        args = (user, pwd, lookback, limit, outdir, do_inventory, only_schema, table_like, self.var_open_folder.get())
        t = threading.Thread(target=self.worker, args=args, daemon=True)
        self.set_running(True)
        self.log("Starting export …")
        t.start()

    # ------------------- Background worker -------------------
    def worker(self, user, pwd, lookback, limit, outdir, do_inventory, only_schema, table_like, open_after):
        try:
            self.log(f"Connecting to {PG_HOST}:{PG_PORT}/{PG_DBNAME} …")
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                dbname=PG_DBNAME,
                user=user,
                password=pwd,
                connect_timeout=8,
            )
            self.log("Connected.")

            cur = conn.cursor()

            # ---- Predefined checks ----
            self.log("Running pre-check: SELECT 1 …")
            cur.execute("SELECT 1")
            _ = cur.fetchone()

            self.log("Running pre-check: test access to sdc_owner.issr_profl …")
            cur.execute("SELECT 1 FROM sdc_owner.issr_profl LIMIT 1")

            # ---- Run main custom query ----
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_query = os.path.join(outdir, f"issr_profl_diff_{ts}.csv")
            self.log(f"Executing issr_profl diff (lookback='{lookback}', limit={limit}) …")
            cur.execute(CUSTOM_QUERY, (lookback, limit))
            rows = cur.fetchall()
            header = [d.name for d in cur.description]

            write_csv(out_query, header, rows)
            self.log(f"✔ Wrote query results: {abspath(out_query)}  (rows: {len(rows)})")

            # ---- Optional: Inventory export ----
            if do_inventory:
                self.log("Inventory export requested …")
                # Resolve schemas
                if only_schema:
                    cur.execute("""
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name = %s
                        ORDER BY schema_name
                    """, (only_schema,))
                else:
                    cur.execute("""
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name NOT IN %s
                        ORDER BY schema_name
                    """, (EXCLUDED_SCHEMAS,))

                schemas = [r[0] for r in cur.fetchall()]
                if not schemas:
                    self.log("No matching schemas found; skipping inventory.")
                else:
                    tables_rows = []
                    for s in schemas:
                        if table_like:
                            cur.execute("""
                                SELECT table_schema, table_name, table_type
                                FROM information_schema.tables
                                WHERE table_schema = %s
                                  AND table_name ILIKE %s
                                ORDER BY table_name
                            """, (s, table_like))
                        else:
                            cur.execute("""
                                SELECT table_schema, table_name, table_type
                                FROM information_schema.tables
                                WHERE table_schema = %s
                                ORDER BY table_name
                            """, (s,))
                        for sch, tbl, ttype in cur.fetchall():
                            kind = "TABLE" if ttype.upper() == "BASE TABLE" else ttype.upper()
                            tables_rows.append((sch, tbl, kind))

                    out_tables = os.path.join(outdir, f"schemas_tables_{ts}.csv")
                    write_csv(out_tables, ["schema", "table", "type"], tables_rows)
                    self.log(f"✔ Wrote table list: {abspath(out_tables)}  (rows: {len(tables_rows)})")

                    # Columns
                    columns_rows = []
                    tables_by_schema = {}
                    for sch, tbl, _ in tables_rows:
                        tables_by_schema.setdefault(sch, []).append(tbl)

                    for sch, tbls in tables_by_schema.items():
                        cur.execute("""
                            SELECT table_schema, table_name, column_name, data_type, is_nullable, column_default, ordinal_position
                            FROM information_schema.columns
                            WHERE table_schema = %s
                            ORDER BY table_name, ordinal_position
                        """, (sch,))
                        for row in cur.fetchall():
                            _sch, _tbl, col, dtype, nullable, default, _ord = row
                            if _tbl in tbls:
                                columns_rows.append((_sch, _tbl, col, dtype, nullable, default))

                    out_columns = os.path.join(outdir, f"columns_{ts}.csv")
                    write_csv(out_columns, ["schema", "table", "column_name", "data_type", "is_nullable", "column_default"], columns_rows)
                    self.log(f"✔ Wrote columns list: {abspath(out_columns)}  (rows: {len(columns_rows)})")

            cur.close()
            conn.close()
            self.log("Closed connection.")
            self.log("All done.")
            if open_after:
                try:
                    os.startfile(outdir)  # Windows-only
                except Exception:
                    pass

        except psycopg2.OperationalError as e:
            self.log(f"OperationalError: {e}")
            messagebox.showerror("OperationalError", str(e))
        except Exception as e:
            self.log(f"Error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.after(0, self.set_running, False)

# ------------------- Main Entry -------------------
if __name__ == "__main__":
    app = PgExporterApp()
    app.mainloop()