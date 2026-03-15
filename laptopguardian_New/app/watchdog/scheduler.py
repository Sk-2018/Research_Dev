"""
Background watchdog scheduler.
Runs as a daemon thread from main.py.
Samples telemetry, scores risk, applies actions, writes to DB.
"""
import time, logging, threading
from app.collector import collect_all
from app.risk.scorer import compute as score_risk, TIER_WARN, TIER_CRITICAL
from app.watchdog.ats_evaluator import evaluate as evaluate_ats
from app.watchdog.actions import (
    switch_to_power_saver, restore_power_plan,
    lower_process_priority, toast_notification,
    request_process_termination,
)

logger = logging.getLogger(__name__)

_latest_telemetry: dict = {}
_latest_risk = None
_latest_ats = None
_lock = threading.Lock()
_cool_cycles = 0
_last_ats_toast_at = 0.0
COOL_RESTORE_CYCLES = 10   # ~30s at 3s interval before restoring plan


def get_latest():
    with _lock:
        return _latest_telemetry, _latest_risk


def get_latest_ats():
    with _lock:
        return _latest_ats


def run_loop(db, cfg: dict, stop_event: threading.Event):
    global _latest_telemetry, _latest_risk, _latest_ats, _cool_cycles, _last_ats_toast_at
    interval  = cfg.get("general", {}).get("sample_interval_seconds", 3)
    top_n     = cfg.get("general", {}).get("top_n_processes", 10)
    dry_run   = cfg.get("general", {}).get("dry_run", False)
    retention = cfg.get("general", {}).get("log_retention_days", 7)
    actions   = cfg.get("actions", {})
    ats_cfg   = cfg.get("ats", {})
    allowlist = cfg.get("process_allowlist", {})
    priority_allowlist = allowlist.get("priority_lower", [])
    kill_allowlist     = allowlist.get("kill_candidates", [])
    ats_enabled = ats_cfg.get("enabled", False)
    ats_toast_threshold = float(ats_cfg.get("maintenance_toast_threshold", 40.0))
    ats_toast_cooldown = max(0, int(ats_cfg.get("toast_cooldown_seconds", 1800)))

    logger.info(f"Watchdog started (interval={interval}s, dry_run={dry_run})")
    last_purge = time.time()

    while not stop_event.is_set():
        try:
            telemetry = collect_all(top_n)
            risk = score_risk(telemetry, cfg)
            ats_result = evaluate_ats(telemetry, cfg) if ats_enabled else None

            with _lock:
                _latest_telemetry = telemetry
                _latest_risk = risk
                _latest_ats = ats_result

            db.insert_metric(telemetry, risk.score, risk.tier)

            now = time.time()
            if (
                ats_result
                and ats_result.maintenance_score >= ats_toast_threshold
                and (now - _last_ats_toast_at) >= ats_toast_cooldown
            ):
                top_reason = ats_result.top_reasons[0] if ats_result.top_reasons else ats_result.verdict
                message = f"ATS score {ats_result.maintenance_score:.0f}/100. {top_reason}"
                toast_notification("Guardian Maintenance Recommended", message)
                db.insert_alert("ADVISORY", f"ATS maintenance recommended: {message}")
                _last_ats_toast_at = now

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
