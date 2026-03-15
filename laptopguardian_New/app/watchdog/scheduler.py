"""
Background watchdog scheduler.
Runs as a daemon thread from main.py.
Samples telemetry, scores risk, applies actions, writes to DB.
"""
import time, logging, threading
from app.collector import collect_all
from app.risk.scorer import compute as score_risk, TIER_WARN, TIER_CRITICAL
from app.watchdog.actions import (
    switch_to_power_saver, restore_power_plan,
    lower_process_priority, toast_notification,
    request_process_termination
)

logger = logging.getLogger(__name__)

_latest_telemetry: dict = {}
_latest_risk = None
_lock = threading.Lock()
_cool_cycles = 0
COOL_RESTORE_CYCLES = 10   # ~30s at 3s interval before restoring plan


def get_latest():
    with _lock:
        return _latest_telemetry, _latest_risk


def run_loop(db, cfg: dict, stop_event: threading.Event):
    global _latest_telemetry, _latest_risk, _cool_cycles
    interval  = cfg.get("general", {}).get("sample_interval_seconds", 3)
    top_n     = cfg.get("general", {}).get("top_n_processes", 10)
    dry_run   = cfg.get("general", {}).get("dry_run", False)
    retention = cfg.get("general", {}).get("log_retention_days", 7)
    actions   = cfg.get("actions", {})
    allowlist = cfg.get("process_allowlist", {})
    priority_allowlist = allowlist.get("priority_lower", [])
    kill_allowlist     = allowlist.get("kill_candidates", [])

    logger.info(f"Watchdog started (interval={interval}s, dry_run={dry_run})")
    last_purge = time.time()

    while not stop_event.is_set():
        try:
            telemetry = collect_all(top_n)
            risk = score_risk(telemetry, cfg)

            with _lock:
                _latest_telemetry = telemetry
                _latest_risk = risk

            db.insert_metric(telemetry, risk.score, risk.tier)

            if risk.tier in (TIER_WARN, TIER_CRITICAL):
                db.insert_alert(risk.tier, risk.reason)
                logger.warning(f"[{risk.tier}] Score={risk.score} | {risk.reason}")

                if risk.tier == TIER_WARN and actions.get("switch_power_saver_on_warn", True):
                    switch_to_power_saver(dry_run)
                    _cool_cycles = 0

                if risk.tier == TIER_WARN and actions.get("lower_process_priority_on_warn", True):
                    procs = telemetry.get("cpu", {}).get("top_processes", [])
                    for p in procs[:3]:
                        lower_process_priority(
                            p["pid"], p["name"], priority_allowlist, dry_run
                        )

                if risk.tier == TIER_CRITICAL:
                    if actions.get("toast_on_critical", True):
                        toast_notification(
                            "🔥 Guardian CRITICAL",
                            f"Risk={risk.score:.0f}/100 | {risk.reason}"
                        )
                    procs = telemetry.get("cpu", {}).get("top_processes", [])
                    if procs:
                        top = procs[0]
                        request_process_termination(
                            top["pid"], top["name"], kill_allowlist, dry_run
                        )
            else:
                _cool_cycles += 1
                if (
                    _cool_cycles >= COOL_RESTORE_CYCLES
                    and actions.get("restore_power_plan_on_cool", True)
                ):
                    restore_power_plan(dry_run)
                    _cool_cycles = 0

            # Purge old records once per hour
            if time.time() - last_purge > 3600:
                db.purge_old(retention)
                last_purge = time.time()

        except Exception as e:
            logger.error(f"Watchdog loop error: {e}", exc_info=True)

        stop_event.wait(timeout=interval)

    logger.info("Watchdog stopped.")
