import argparse
import time

from app.configuration import load_config
from app.logging_utils import configure_logging
from app.storage.db import Database
from app.ui.dashboard import create_dashboard
from app.watchdog.daemon import WatchdogDaemon


def _parse_args():
    parser = argparse.ArgumentParser(description="Laptop Health Guardian")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--headless", action="store_true", help="Run watchdog daemon without dashboard")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run action mode for this run")
    return parser.parse_args()


def main():
    args = _parse_args()
    config = load_config(args.config)
    if args.dry_run:
        config["actions"]["dry_run"] = True

    logger = configure_logging(config["system"]["log_path"])
    db = Database(config["system"]["db_path"])

    logger.info("Starting Jarvis watchdog")
    daemon = WatchdogDaemon(config, db, logger)
    daemon.start()

    if args.headless:
        logger.info("Headless mode enabled. Press Ctrl+C to stop.")
        try:
            while daemon.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        finally:
            daemon.stop()
            daemon.join(timeout=5)
        return

    host = config["dashboard"]["host"]
    port = int(config["dashboard"]["port"])
    logger.info("Starting dashboard at http://%s:%s", host, port)
    dash_app = create_dashboard(db, config)
    try:
        # Dash 3 uses app.run(); Dash 2 used app.run_server().
        if hasattr(dash_app, "run"):
            dash_app.run(debug=False, port=port, host=host)
        else:
            dash_app.run_server(debug=False, port=port, host=host)
    finally:
        daemon.stop()
        daemon.join(timeout=5)


if __name__ == "__main__":
    main()
