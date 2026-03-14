import json
import sqlite3
import threading

import pandas as pd


class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.create_tables()

    def create_tables(self):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_percent REAL NOT NULL,
                    ram_percent REAL NOT NULL,
                    temp_c REAL NOT NULL,
                    risk_score REAL NOT NULL,
                    top_processes TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    risk_score REAL NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    details TEXT NOT NULL
                )
                """
            )
            self.conn.commit()

    def insert_metric(self, cpu, ram, temp, risk, procs):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO metrics (cpu_percent, ram_percent, temp_c, risk_score, top_processes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (float(cpu), float(ram), float(temp), float(risk), json.dumps(procs)),
            )
            self.conn.commit()

    def insert_action(self, risk_score, action, target, reason, outcome, details=None):
        details = details or {}
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO actions (risk_score, action, target, reason, outcome, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    float(risk_score),
                    str(action),
                    str(target or ""),
                    str(reason or ""),
                    str(outcome),
                    json.dumps(details),
                ),
            )
            self.conn.commit()

    def get_recent(self, limit=120):
        safe_limit = max(1, int(limit))
        with self._lock:
            return pd.read_sql_query(
                "SELECT timestamp, cpu_percent, ram_percent, temp_c, risk_score, top_processes FROM metrics ORDER BY timestamp DESC LIMIT ?",
                self.conn,
                params=(safe_limit,),
            )

    def get_recent_actions(self, limit=50):
        safe_limit = max(1, int(limit))
        with self._lock:
            return pd.read_sql_query(
                "SELECT timestamp, risk_score, action, target, reason, outcome, details FROM actions ORDER BY timestamp DESC LIMIT ?",
                self.conn,
                params=(safe_limit,),
            )
