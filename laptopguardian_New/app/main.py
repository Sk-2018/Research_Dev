"""
Laptop Health Guardian - Entry Point.
Starts background watchdog thread, then launches Dash dashboard.
"""
import sys, os, yaml, logging, threading, logging.handlers
from pathlib import Path

def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def setup_logging(cfg: dict):
    log_path = cfg.get("general", {}).get("log_path", "logs/guardian.log")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    # Rolling file handler: 5 MB × 5 files
    fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=5)
    fh.setFormatter(fmt)
    root.addHandler(fh)
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)


def check_admin():
    import ctypes
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def main():
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
        target=run_loop, args=(db, cfg, stop_event), daemon=True, name="Watchdog"
    )
    watchdog_thread.start()
    logger.info("Watchdog daemon started.")

    from app.ui.dashboard import create_dashboard
    dash_app = create_dashboard(db, cfg)

    host = cfg.get("dashboard", {}).get("host", "127.0.0.1")
    port = cfg.get("dashboard", {}).get("port", 8050)
    logger.info(f"Dashboard starting at http://{host}:{port}")
    print(f"\n  ✅  Open browser → http://{host}:{port}\n")

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
