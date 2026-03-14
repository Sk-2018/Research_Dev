"""Battery: charge %, plugged status, discharge rate, health estimate."""
import psutil, subprocess, logging, json
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BatterySnapshot:
    charge_pct: Optional[float] = None
    plugged: Optional[bool] = None
    seconds_left: Optional[int] = None
    discharge_rate_w: Optional[float] = None
    design_capacity_mwh: Optional[int] = None
    full_capacity_mwh: Optional[int] = None
    wear_pct: Optional[float] = None   # (1 - full/design)*100


def _wmi_battery_health() -> tuple[Optional[int], Optional[int]]:
    ps = (
        "$b = Get-WmiObject -Class BatteryStaticData -Namespace root/wmi 2>$null | Select-Object -First 1; "
        "$f = Get-WmiObject -Class BatteryFullChargedCapacity -Namespace root/wmi 2>$null | Select-Object -First 1; "
        "if($b -and $f){ [PSCustomObject]@{Design=$b.DesignedCapacity; Full=$f.FullChargedCapacity} | ConvertTo-Json }"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=8
        )
        d = json.loads(r.stdout.strip())
        return d.get("Design"), d.get("Full")
    except Exception as e:
        logger.debug(f"Battery health WMI failed: {e}")
    return None, None


def collect() -> BatterySnapshot:
    snap = BatterySnapshot()
    bat = psutil.sensors_battery()
    if bat:
        snap.charge_pct = round(bat.percent, 1)
        snap.plugged = bat.power_plugged
        snap.seconds_left = bat.secsleft if bat.secsleft not in (-1, -2) else None
    design, full = _wmi_battery_health()
    snap.design_capacity_mwh = design
    snap.full_capacity_mwh = full
    if design and full and design > 0:
        snap.wear_pct = round((1 - full / design) * 100, 1)
    return snap


def get_battery_status() -> dict:
    """Wrapper function for API compatibility."""
    snap = collect()
    return {
        "percent": snap.charge_pct or 0,
        "plugged": snap.plugged or False,
        "seconds_left": snap.seconds_left,
        "discharge_rate_w": snap.discharge_rate_w,
    }
