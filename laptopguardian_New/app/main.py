from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.configuration import load_config
from app.logging_utils import configure_logging
from app.storage.db import GuardianDB
from app.ui.dashboard import create_dashboard
from app.watchdog.scheduler import GuardianScheduler


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Laptop Health Guardian")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config")
    parser.add_argument("--headless", action="store_true", help="Run scheduler only, no dashboard")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run action mode")
    parser.add_argument("--once", action="store_true", help="Run one telemetry cycle and exit")
    return parser.parse_args()


def _prepare_runtime_paths(config: dict) -> None:
    db_path = Path(str(config["general"]["db_path"]))
    log_path = Path(str(config["general"]["log_path"]))
    if db_path.parent != Path(""):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = _parse_args()
    config = load_config(args.config)
    if args.dry_run:
        config["general"]["dry_run"] = True

    _prepare_runtime_paths(config)
    logger = configure_logging(str(config["general"]["log_path"]))
    db = GuardianDB(str(config["general"]["db_path"]))

    scheduler = GuardianScheduler(config=config, db=db, logger=logger)
    if args.once:
        try:
            scheduler.run_cycle()
            logger.info("Completed one cycle successfully.")
        finally:
            db.close()
        return

    scheduler.start()
    if args.headless:
        logger.info("Headless mode running. Press Ctrl+C to stop.")
        try:
            while scheduler.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
        finally:
            scheduler.stop()
            scheduler.join(timeout=5)
            db.close()
        return

    host = str(config["dashboard"]["host"])
    port = int(config["dashboard"]["port"])
    logger.info("Dashboard running at http://%s:%s", host, port)
    app = create_dashboard(db, config)
    try:
        # Dash 3 uses app.run(); Dash 2 used app.run_server().
        if hasattr(app, "run"):
            app.run(debug=False, host=host, port=port)
        else:
            app.run_server(debug=False, host=host, port=port)
    finally:
        scheduler.stop()
        scheduler.join(timeout=5)
        db.close()


if __name__ == "__main__":
    main()
