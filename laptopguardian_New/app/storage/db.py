"""
SQLite storage with schema migration support.
Tables: metrics (time-series), alerts (alert history).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime
from typing import List


logger = logging.getLogger(__name__)

METRICS_TABLE_SQL = """
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
)
"""

ALERTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    tier         TEXT,
    message      TEXT,
    action_taken TEXT
)
"""

CREATE_METRICS_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts)"
CREATE_ALERTS_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(ts)"

EXPECTED_METRICS_COLUMNS = {
    "id",
    "ts",
    "cpu_pct",
    "temp_c",
    "ram_pct",
    "disk_read",
    "disk_write",
    "risk_score",
    "risk_tier",
    "raw_json",
}

EXPECTED_ALERTS_COLUMNS = {"id", "ts", "tier", "message", "action_taken"}


def _parse_timestamp(value) -> float:
    if value is None:
        return time.time()
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return time.time()

    try:
        return float(text)
    except ValueError:
        pass

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue

    return time.time()


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


class Database:
    def __init__(self, db_path: str = "guardian.db"):
        self.path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._initialize_schema()
        logger.info("Database ready at %s", db_path)

    def _initialize_schema(self) -> None:
        self._ensure_metrics_table()
        self._ensure_alerts_table()
        self.conn.commit()

    def _ensure_metrics_table(self) -> None:
        columns = set(_table_columns(self.conn, "metrics"))
        if not columns:
            self.conn.execute(METRICS_TABLE_SQL)
            self.conn.execute(CREATE_METRICS_INDEX_SQL)
            return

        if EXPECTED_METRICS_COLUMNS.issubset(columns):
            self.conn.execute(CREATE_METRICS_INDEX_SQL)
            return

        self._migrate_metrics_table()
        self.conn.execute(CREATE_METRICS_INDEX_SQL)

    def _ensure_alerts_table(self) -> None:
        columns = set(_table_columns(self.conn, "alerts"))
        if not columns:
            self.conn.execute(ALERTS_TABLE_SQL)
            self.conn.execute(CREATE_ALERTS_INDEX_SQL)
            return

        if EXPECTED_ALERTS_COLUMNS.issubset(columns):
            self.conn.execute(CREATE_ALERTS_INDEX_SQL)
            return

        self._migrate_alerts_table()
        self.conn.execute(CREATE_ALERTS_INDEX_SQL)

    def _migrate_metrics_table(self) -> None:
        backup_name = f"metrics_legacy_{int(time.time())}"
        self.conn.execute(f"ALTER TABLE metrics RENAME TO {backup_name}")
        self.conn.execute(METRICS_TABLE_SQL)

        cursor = self.conn.execute(f"SELECT * FROM {backup_name}")
        source_columns = [description[0] for description in cursor.description]
        migrated_rows = []

        for source_row in cursor.fetchall():
            row = dict(zip(source_columns, source_row))
            raw_json = row.get("raw_json")
            if not raw_json:
                raw_json = json.dumps({"legacy_metrics_row": row}, default=str)

            migrated_rows.append(
                (
                    row.get("id"),
                    _parse_timestamp(row.get("ts", row.get("timestamp"))),
                    row.get("cpu_pct", row.get("cpu_percent")),
                    row.get("temp_c"),
                    row.get("ram_pct", row.get("ram_percent")),
                    row.get("disk_read"),
                    row.get("disk_write"),
                    row.get("risk_score"),
                    row.get("risk_tier", row.get("risk_level")),
                    raw_json,
                )
            )

        if migrated_rows:
            self.conn.executemany(
                """
                INSERT INTO metrics(
                    id, ts, cpu_pct, temp_c, ram_pct, disk_read, disk_write, risk_score, risk_tier, raw_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                migrated_rows,
            )

        logger.warning(
            "Migrated legacy metrics table to current schema; backup preserved as %s",
            backup_name,
        )

    def _migrate_alerts_table(self) -> None:
        backup_name = f"alerts_legacy_{int(time.time())}"
        self.conn.execute(f"ALTER TABLE alerts RENAME TO {backup_name}")
        self.conn.execute(ALERTS_TABLE_SQL)

        cursor = self.conn.execute(f"SELECT * FROM {backup_name}")
        source_columns = [description[0] for description in cursor.description]
        migrated_rows = []

        for source_row in cursor.fetchall():
            row = dict(zip(source_columns, source_row))
            migrated_rows.append(
                (
                    row.get("id"),
                    _parse_timestamp(row.get("ts", row.get("timestamp"))),
                    row.get("tier", row.get("level", row.get("risk_level"))),
                    row.get("message", row.get("reason", "")),
                    row.get("action_taken", row.get("action", "")),
                )
            )

        if migrated_rows:
            self.conn.executemany(
                "INSERT INTO alerts(id, ts, tier, message, action_taken) VALUES(?,?,?,?,?)",
                migrated_rows,
            )

        logger.warning(
            "Migrated legacy alerts table to current schema; backup preserved as %s",
            backup_name,
        )

    def insert_metric(self, telemetry: dict, risk_score: float, risk_tier: str):
        cpu = telemetry.get("cpu", {})
        mem = telemetry.get("memory", {})
        disk = telemetry.get("disk", {})
        self.conn.execute(
            "INSERT INTO metrics(ts,cpu_pct,temp_c,ram_pct,disk_read,disk_write,risk_score,risk_tier,raw_json) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                _parse_timestamp(telemetry.get("timestamp", time.time())),
                cpu.get("total_pct"),
                cpu.get("temp_celsius"),
                mem.get("ram_pct"),
                disk.get("read_mb_s"),
                disk.get("write_mb_s"),
                risk_score,
                risk_tier,
                json.dumps(telemetry, default=str),
            ),
        )
        self.conn.commit()

    def insert_alert(self, tier: str, message: str, action_taken: str = ""):
        self.conn.execute(
            "INSERT INTO alerts(ts, tier, message, action_taken) VALUES(?,?,?,?)",
            (time.time(), tier, message, action_taken),
        )
        self.conn.commit()

    def get_metrics(self, minutes: int = 30) -> List[dict]:
        cutoff = time.time() - minutes * 60
        rows = self.conn.execute(
            "SELECT ts,cpu_pct,temp_c,ram_pct,disk_read,disk_write,risk_score,risk_tier "
            "FROM metrics WHERE ts > ? ORDER BY ts ASC",
            (cutoff,),
        ).fetchall()
        keys = ["ts", "cpu_pct", "temp_c", "ram_pct", "disk_read", "disk_write", "risk_score", "risk_tier"]
        return [dict(zip(keys, row)) for row in rows]

    def get_alerts(self, hours: int = 24) -> List[dict]:
        cutoff = time.time() - hours * 3600
        rows = self.conn.execute(
            "SELECT ts, tier, message, action_taken FROM alerts WHERE ts > ? ORDER BY ts DESC",
            (cutoff,),
        ).fetchall()
        return [{"ts": row[0], "tier": row[1], "message": row[2], "action": row[3]} for row in rows]

    def purge_old(self, retention_days: int = 7):
        cutoff = time.time() - retention_days * 86400
        self.conn.execute("DELETE FROM metrics WHERE ts < ?", (cutoff,))
        self.conn.execute("DELETE FROM alerts WHERE ts < ?", (cutoff,))
        self.conn.commit()

    def export_csv(self, minutes: int = 60) -> str:
        import csv
        import io

        rows = self.get_metrics(minutes)
        if not rows:
            return ""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()


# Backward compatibility for older imports that still reference GuardianDB.
GuardianDB = Database
