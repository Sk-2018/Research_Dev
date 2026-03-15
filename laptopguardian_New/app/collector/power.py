"""Active Windows power plan name and GUID via powercfg."""
import subprocess, re, logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

POWER_SAVER_GUID = "a1841308-3541-4fab-bc81-f71556f20b4a"
BALANCED_GUID    = "381b4222-f694-41f0-9685-ff5bb260df2e"
HIGH_PERF_GUID   = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

KNOWN_PLANS = {
    POWER_SAVER_GUID: "Power Saver",
    BALANCED_GUID: "Balanced",
    HIGH_PERF_GUID: "High Performance",
}


@dataclass
class PowerSnapshot:
    plan_guid: Optional[str] = None
    plan_name: str = "Unknown"
    is_plugged_in: Optional[bool] = None


def get_active_plan() -> tuple[Optional[str], str]:
    try:
        r = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True, text=True, timeout=5
        )
        m = re.search(r"([0-9a-f\-]{36})\s+\((.+?)\)", r.stdout, re.IGNORECASE)
        if m:
            guid = m.group(1).lower()
            name = m.group(2).strip()
            return guid, name
    except Exception as e:
        logger.warning(f"powercfg query failed: {e}")
    return None, "Unknown"


def collect() -> PowerSnapshot:
    snap = PowerSnapshot()
    snap.plan_guid, snap.plan_name = get_active_plan()
    import psutil
    bat = psutil.sensors_battery()
    if bat:
        snap.is_plugged_in = bat.power_plugged
    return snap
