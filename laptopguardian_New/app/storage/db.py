"""
SQLite storage with rolling retention.
Tables: metrics (time-series), alerts (alert history).
"""
import sqlite3, json, logging, time
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    cpu_pct     REAL,
    temp_c      REAL,
    ram_pct     REAL,
    disk_read   REAL,
    disk_write  REAL,
    risk_score  REAL,
    risk_tier   TEXT,
    raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    tier        TEXT,
    message     TEXT,
    action_taken TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts);
"""


class Database:
    def __init__(self, db_path: str = "guardian.db"):
        self.path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        logger.info(f"Database ready at {db_path}")

    def insert_metric(self, telemetry: dict, risk_score: float, risk_tier: str):
        cpu  = telemetry.get("cpu", {})
        mem  = telemetry.get("memory", {})
        disk = telemetry.get("disk", {})
        self.conn.execute(
            "INSERT INTO metrics(ts,cpu_pct,temp_c,ram_pct,disk_read,disk_write,risk_score,risk_tier,raw_json) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                telemetry.get("timestamp", time.time()),
                cpu.get("total_pct"),
                cpu.get("temp_celsius"),
                mem.get("ram_pct"),
                disk.get("read_mb_s"),
                disk.get("write_mb_s"),
                risk_score,
                risk_tier,
                json.dumps(telemetry),
            )
        )
        self.conn.commit()

    def insert_alert(self, tier: str, message: str, action_taken: str = ""):
        self.conn.execute(
            "INSERT INTO alerts(ts, tier, message, action_taken) VALUES(?,?,?,?)",
            (time.time(), tier, message, action_taken)
        )
        self.conn.commit()

    def get_metrics(self, minutes: int = 30) -> List[dict]:
        cutoff = time.time() - minutes * 60
        rows = self.conn.execute(
            "SELECT ts,cpu_pct,temp_c,ram_pct,disk_read,disk_write,risk_score,risk_tier "
            "FROM metrics WHERE ts > ? ORDER BY ts ASC", (cutoff,)
        ).fetchall()
        keys = ["ts","cpu_pct","temp_c","ram_pct","disk_read","disk_write","risk_score","risk_tier"]
        return [dict(zip(keys, r)) for r in rows]

    def get_alerts(self, hours: int = 24) -> List[dict]:
        cutoff = time.time() - hours * 3600
        rows = self.conn.execute(
            "SELECT ts, tier, message, action_taken FROM alerts WHERE ts > ? ORDER BY ts DESC",
            (cutoff,)
        ).fetchall()
        return [{"ts": r[0], "tier": r[1], "message": r[2], "action": r[3]} for r in rows]

    def purge_old(self, retention_days: int = 7):
        cutoff = time.time() - retention_days * 86400
        self.conn.execute("DELETE FROM metrics WHERE ts < ?", (cutoff,))
        self.conn.execute("DELETE FROM alerts WHERE ts < ?", (cutoff,))
        self.conn.commit()

    def export_csv(self, minutes: int = 60) -> str:
        import csv, io
        rows = self.get_metrics(minutes)
        if not rows:
            return ""
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue()
