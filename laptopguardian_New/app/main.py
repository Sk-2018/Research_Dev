"""
Laptop Health Guardian entry point.
Starts the watchdog thread, then launches the Dash dashboard.
"""
from __future__ import annotations

import copy
import logging
import logging.handlers
import sys
import threading
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in (None, "") and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.configuration import load_config as load_app_config


def _resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def load_config(path: str | Path = PROJECT_ROOT / "config.yaml") -> dict:
    config_path = _resolve_project_path(path)
    cfg = copy.deepcopy(load_app_config(str(config_path)))

    general = cfg.setdefault("general", {})
    ats = cfg.setdefault("ats", {})

    general["db_path"] = str(_resolve_project_path(general.get("db_path", "guardian.db")))
    general["log_path"] = str(_resolve_project_path(general.get("log_path", "logs/guardian.log")))
    ats["script_path"] = str(_resolve_project_path(ats.get("script_path", "..\\ATS_Maintenance_Aspire.bat")))

    return cfg


def setup_logging(cfg: dict) -> None:
    log_path = cfg.get("general", {}).get("log_path", "logs/guardian.log")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if root.handlers:
        return

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)


def check_admin() -> bool:
    import ctypes

    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def main() -> None:
    cfg = load_config()
    setup_logging(cfg)
    logger = logging.getLogger("main")

    if not check_admin():
        logger.warning(
            "Not running as Administrator. WMI temperature queries and powercfg "
            "actions may be limited. Right-click PowerShell and 'Run as Administrator' "
            "for full functionality."
        )

    from app.storage.db import Database

    db_path = cfg.get("general", {}).get("db_path", "guardian.db")
    db = Database(db_path)

    stop_event = threading.Event()

    from app.watchdog.scheduler import run_loop

    watchdog_thread = threading.Thread(
        target=run_loop,
        args=(db, cfg, stop_event),
        daemon=True,
        name="Watchdog",
    )
    watchdog_thread.start()
    logger.info("Watchdog daemon started.")

    from app.ui.dashboard import create_dashboard

    dash_app = create_dashboard(db, cfg)

    host = cfg.get("dashboard", {}).get("host", "127.0.0.1")
    port = cfg.get("dashboard", {}).get("port", 8050)
    logger.info("Dashboard starting at http://%s:%s", host, port)
    print(f"\n  Open browser -> http://{host}:{port}\n")

    try:
        dash_app.run(debug=False, host=host, port=port, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Shutting down Guardian...")
    finally:
        stop_event.set()
        watchdog_thread.join(timeout=10)
        logger.info("Goodbye.")


if __name__ == "__main__":
    main()
