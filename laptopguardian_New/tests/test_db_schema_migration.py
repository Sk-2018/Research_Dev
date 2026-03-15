import sqlite3
import unittest
from datetime import datetime, timezone
from pathlib import Path
import uuid

from app.storage.db import Database


LEGACY_METRICS_SCHEMA = """
CREATE TABLE metrics (
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


class TestDatabaseSchemaMigration(unittest.TestCase):
    def test_legacy_metrics_table_is_migrated_in_place(self) -> None:
        db_path = Path.cwd() / f"test_guardian_{uuid.uuid4().hex}.db"
        db = None
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(LEGACY_METRICS_SCHEMA)
            conn.execute(
                """
                INSERT INTO metrics(
                    timestamp, cpu_percent, ram_percent, disk_percent, temp_c,
                    gpu_percent, gpu_temp_c, battery_percent, risk_score,
                    risk_level, risk_flags, top_processes
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    42.5,
                    68.0,
                    74.0,
                    81.0,
                    None,
                    None,
                    95.0,
                    72,
                    "WARN",
                    "legacy-risk",
                    "[]",
                ),
            )
            conn.commit()
            conn.close()

            db = Database(str(db_path))
            metrics = db.get_metrics(minutes=60)
            metric_columns = [row[1] for row in db.conn.execute("PRAGMA table_info(metrics)").fetchall()]
            alert_columns = [row[1] for row in db.conn.execute("PRAGMA table_info(alerts)").fetchall()]

            self.assertEqual(len(metrics), 1)
            self.assertIn("ts", metric_columns)
            self.assertIn("raw_json", metric_columns)
            self.assertIn("ts", alert_columns)
            self.assertAlmostEqual(metrics[0]["cpu_pct"], 42.5)
            self.assertAlmostEqual(metrics[0]["ram_pct"], 68.0)
            self.assertEqual(metrics[0]["risk_tier"], "WARN")
        finally:
            if db is not None:
                db.conn.close()
            if db_path.exists():
                db_path.unlink()


if __name__ == "__main__":
    unittest.main()
