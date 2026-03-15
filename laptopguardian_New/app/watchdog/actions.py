"""
Mitigation actions for the watchdog.
All destructive actions require allowlist check + dry_run guard.
"""
import subprocess, logging, ctypes, psutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

POWER_SAVER_GUID = "a1841308-3541-4fab-bc81-f71556f20b4a"
_previous_plan: Optional[str] = None


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _run_powercfg(args: list, dry_run: bool = False) -> bool:
    if dry_run:
        logger.info(f"[DRY RUN] powercfg {' '.join(args)}")
        return True
    try:
        r = subprocess.run(["powercfg"] + args, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True
        logger.warning(f"powercfg failed: {r.stderr.strip()}")
    except Exception as e:
        logger.error(f"powercfg error: {e}")
    return False


def switch_to_power_saver(dry_run: bool = False) -> bool:
    global _previous_plan
    from app.collector.power import get_active_plan
    guid, name = get_active_plan()
    if guid and guid.lower() != POWER_SAVER_GUID:
        _previous_plan = guid
    ok = _run_powercfg(["/setactive", POWER_SAVER_GUID], dry_run)
    if ok:
        logger.info("Switched to Power Saver plan.")
    return ok


def restore_power_plan(dry_run: bool = False) -> bool:
    global _previous_plan
    if not _previous_plan:
        logger.info("No previous plan stored; skipping restore.")
        return False
    ok = _run_powercfg(["/setactive", _previous_plan], dry_run)
    if ok:
        logger.info(f"Restored power plan: {_previous_plan}")
        _previous_plan = None
    return ok


def lower_process_priority(pid: int, name: str, allowlist: list, dry_run: bool = False) -> bool:
    if name.lower() not in [a.lower() for a in allowlist]:
        logger.warning(f"Process {name} ({pid}) not in priority allowlist; skipping.")
        return False
    if dry_run:
        logger.info(f"[DRY RUN] Would lower priority of {name} ({pid})")
        return True
    try:
        p = psutil.Process(pid)
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        logger.info(f"Lowered priority of {name} ({pid})")
        return True
    except Exception as e:
        logger.error(f"Could not lower priority of {name} ({pid}): {e}")
    return False


def toast_notification(title: str, message: str):
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=8, threaded=True)
    except Exception as e:
        logger.warning(f"Toast notification failed: {e}")


def request_process_termination(pid: int, name: str, kill_allowlist: list, dry_run: bool = False) -> bool:
    """Requires explicit user confirmation via toast + allowlist check."""
    if name.lower() not in [a.lower() for a in kill_allowlist]:
        logger.warning(f"Kill blocked: {name} not in kill_allowlist.")
        return False
    if dry_run:
        logger.info(f"[DRY RUN] Would request termination of {name} ({pid})")
        return True
    # Toast user for confirmation (non-blocking; action taken only after confirmation via dashboard)
    toast_notification(
        "⚠️ Guardian CRITICAL",
        f"CRITICAL heat! Propose terminating {name} ({pid}). Confirm in dashboard."
    )
    logger.warning(f"Termination proposed for {name} ({pid}). Awaiting user confirmation.")
    return True   # Actual kill happens only via confirmed dashboard action


def run_maintenance_script(script_path: str, dry_run: bool = False) -> bool:
    script = Path(script_path)
    if not script.exists():
        logger.warning("ATS maintenance script not found: %s", script)
        return False

    if dry_run:
        logger.info("[DRY RUN] Would run ATS maintenance script: %s", script)
        return True

    try:
        subprocess.Popen(
            ["cmd.exe", "/c", str(script)],
            cwd=str(script.parent),
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        logger.info("Started ATS maintenance script: %s", script)
        return True
    except Exception as exc:
        logger.error("Failed to start ATS maintenance script %s: %s", script, exc)
        return False
