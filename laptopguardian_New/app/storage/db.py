from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GuardianDB:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL NOT NULL,
                    ram_percent REAL NOT NULL,
                    disk_percent REAL NOT NULL,
                    temp_c REAL NOT NULL,
                    gpu_percent REAL,
                    gpu_temp_c REAL,
                    battery_percent REAL,
                    risk_score INTEGER NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_flags TEXT NOT NULL,
                    top_processes TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    risk_score INTEGER NOT NULL,
                    risk_level TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    details TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ats_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    maintenance_score REAL NOT NULL,
                    verdict TEXT NOT NULL,
                    signals TEXT NOT NULL,
                    top_reasons TEXT NOT NULL,
                    fresh_scan INTEGER NOT NULL
                )
                """
            )
            self._conn.commit()

    def insert_metric(self, snapshot: dict[str, Any], assessment: dict[str, Any]) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO metrics (
                    timestamp, cpu_percent, ram_percent, disk_percent, temp_c,
                    gpu_percent, gpu_temp_c, battery_percent, risk_score,
                    risk_level, risk_flags, top_processes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(snapshot.get("timestamp", "")),
                    float(snapshot.get("cpu_percent", 0.0)),
                    float(snapshot.get("ram_percent", 0.0)),
                    float(snapshot.get("disk_percent", 0.0)),
                    float(snapshot.get("temp_c", -1.0)),
                    snapshot.get("gpu_percent"),
                    snapshot.get("gpu_temp_c"),
                    snapshot.get("battery_percent"),
                    int(assessment.get("risk_score", 0)),
                    str(assessment.get("risk_level", "normal")),
                    json.dumps(assessment.get("risk_flags", [])),
                    json.dumps(snapshot.get("top_processes", [])),
                ),
            )
            self._conn.commit()

    def insert_action(
        self,
        *,
        risk_score: int,
        risk_level: str,
        action: str,
        target: str,
        reason: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO actions (
                    risk_score, risk_level, action, target, reason, outcome, details
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(risk_score),
                    str(risk_level),
                    str(action),
                    str(target),
                    str(reason),
                    str(outcome),
                    json.dumps(details or {}),
                ),
            )
            self._conn.commit()

    def insert_ats_evaluation(self, result: Any) -> None:
        signals = []
        for signal in list(getattr(result, "signals", [])):
            signals.append(
                {
                    "name": getattr(signal, "name", ""),
                    "value": getattr(signal, "value", 0.0),
                    "unit": getattr(signal, "unit", ""),
                    "status": getattr(signal, "status", "OK"),
                    "reason": getattr(signal, "reason", ""),
                    "score_contrib": getattr(signal, "score_contrib", 0.0),
                }
            )

        with self._lock:
            cursor = self._conn.cursor()
            raw_timestamp = getattr(result, "last_evaluated", "")
            if isinstance(raw_timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(raw_timestamp, tz=timezone.utc).isoformat(timespec="seconds")
            else:
                timestamp = str(raw_timestamp)
            cursor.execute(
                """
                INSERT INTO ats_evaluations (
                    timestamp, maintenance_score, verdict, signals, top_reasons, fresh_scan
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    float(getattr(result, "maintenance_score", 0.0)),
                    str(getattr(result, "verdict", "CLEAN")),
                    json.dumps(signals),
                    json.dumps(list(getattr(result, "top_reasons", []))),
                    1 if bool(getattr(result, "fresh_scan", False)) else 0,
                ),
            )
            self._conn.commit()

    def get_recent_metrics(self, limit: int = 300) -> list[dict[str, Any]]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT
                    timestamp, cpu_percent, ram_percent, disk_percent, temp_c,
                    gpu_percent, gpu_temp_c, battery_percent, risk_score,
                    risk_level, risk_flags, top_processes
                FROM metrics
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            )
            rows = cursor.fetchall()

        output: list[dict[str, Any]] = []
        for row in reversed(rows):
            output.append(
                {
                    "timestamp": row[0],
                    "cpu_percent": row[1],
                    "ram_percent": row[2],
                    "disk_percent": row[3],
                    "temp_c": row[4],
                    "gpu_percent": row[5],
                    "gpu_temp_c": row[6],
                    "battery_percent": row[7],
                    "risk_score": row[8],
                    "risk_level": row[9],
                    "risk_flags": json.loads(row[10] or "[]"),
                    "top_processes": json.loads(row[11] or "[]"),
                }
            )
        return output

    def get_latest_metric(self) -> dict[str, Any] | None:
        rows = self.get_recent_metrics(1)
        if not rows:
            return None
        return rows[-1]

    def get_recent_actions(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, risk_score, risk_level, action, target, reason, outcome, details
                FROM actions
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            )
            rows = cursor.fetchall()

        output: list[dict[str, Any]] = []
        for row in rows:
            output.append(
                {
                    "timestamp": row[0],
                    "risk_score": row[1],
                    "risk_level": row[2],
                    "action": row[3],
                    "target": row[4],
                    "reason": row[5],
                    "outcome": row[6],
                    "details": json.loads(row[7] or "{}"),
                }
            )
        return output

    def get_latest_ats_evaluation(self) -> dict[str, Any] | None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, maintenance_score, verdict, signals, top_reasons, fresh_scan
                FROM ats_evaluations
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

        if row is None:
            return None
        return {
            "timestamp": row[0],
            "maintenance_score": row[1],
            "verdict": row[2],
            "signals": json.loads(row[3] or "[]"),
            "top_reasons": json.loads(row[4] or "[]"),
            "fresh_scan": bool(row[5]),
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()


Database = GuardianDB
