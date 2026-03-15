"""Disk I/O throughput, queue length, and free space."""
import psutil, subprocess, logging, json
from dataclasses import dataclass, field
from typing import Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class DiskSnapshot:
    read_mb_s: float = 0.0
    write_mb_s: float = 0.0
    free_gb: float = 0.0
    total_gb: float = 0.0
    used_pct: float = 0.0
    queue_length: Optional[float] = None   # via WMI perf counters


_prev_io = None
_prev_time = None


def _wmi_queue_length() -> Optional[float]:
    ps = (
        "Get-WmiObject -Class Win32_PerfFormattedData_PerfDisk_PhysicalDisk "
        "2>$null | Where-Object{$_.Name -eq '_Total'} | "
        "Select-Object -ExpandProperty CurrentDiskQueueLength"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=6
        )
        val = r.stdout.strip()
        if val:
            return float(val)
    except Exception as e:
        logger.debug(f"Disk queue WMI failed: {e}")
    return None


def collect() -> DiskSnapshot:
    global _prev_io, _prev_time
    import time
    snap = DiskSnapshot()
    usage = psutil.disk_usage("C:\\")
    snap.free_gb = round(usage.free / 1e9, 2)
    snap.total_gb = round(usage.total / 1e9, 2)
    snap.used_pct = usage.percent

    now = time.monotonic()
    io = psutil.disk_io_counters()
    if _prev_io and io:
        dt = now - _prev_time
        snap.read_mb_s = round((io.read_bytes - _prev_io.read_bytes) / 1e6 / dt, 2)
        snap.write_mb_s = round((io.write_bytes - _prev_io.write_bytes) / 1e6 / dt, 2)
    _prev_io = io
    _prev_time = now
    snap.queue_length = _wmi_queue_length()
    return snap


def get_disk_percent() -> float:
    """Wrapper function for API compatibility."""
    usage = psutil.disk_usage("C:\\")
    return usage.percent
