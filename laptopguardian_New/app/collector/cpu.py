"""
CPU Collector: usage, per-core, frequency, temperature, top processes.
Temperature strategies:
  A) WMI MSAcpi_ThermalZone (tenths of Kelvin -> Celsius)
  B) psutil sensors_temperatures (Linux/macOS only; fallback on Windows)
  C) OpenHardwareMonitor WMI namespace (if installed)
"""
import subprocess, json, logging, psutil
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class CPUSnapshot:
    total_pct: float = 0.0
    per_core_pct: List[float] = field(default_factory=list)
    per_core_freq_mhz: List[float] = field(default_factory=list)
    temp_celsius: Optional[float] = None
    temp_source: str = "unavailable"
    top_processes: List[dict] = field(default_factory=list)


def _wmi_acpi_temp() -> Optional[float]:
    """Query MSAcpi_ThermalZone via PowerShell. Returns °C or None."""
    ps = (
        "Get-WmiObject -Namespace root/wmi -Class MSAcpi_ThermalZone "
        "2>$null | Select-Object -First 1 -ExpandProperty CurrentTemperature"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=6
        )
        raw = result.stdout.strip()
        if raw and raw.isdigit():
            return (int(raw) / 10.0) - 273.15
    except Exception as e:
        logger.debug(f"WMI ACPI temp query failed: {e}")
    return None


def _ohm_wmi_temp() -> Optional[float]:
    """Query OpenHardwareMonitor WMI if installed. Returns max CPU temp °C."""
    ps = (
        "Get-WmiObject -Namespace root/OpenHardwareMonitor -Class Sensor "
        "2>$null | Where-Object {$_.SensorType -eq 'Temperature' -and "
        "$_.Name -like '*CPU*'} | Measure-Object -Property Value -Maximum "
        "| Select-Object -ExpandProperty Maximum"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=6
        )
        raw = result.stdout.strip()
        if raw:
            return float(raw)
    except Exception as e:
        logger.debug(f"OHM WMI temp query failed: {e}")
    return None


def _psutil_temp() -> Optional[float]:
    """psutil.sensors_temperatures - works on Linux, mostly unavailable on Windows."""
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for key in ("coretemp", "k10temp", "acpitz", "cpu_thermal"):
                if key in temps:
                    vals = [t.current for t in temps[key] if t.current > 0]
                    if vals:
                        return max(vals)
    except Exception as e:
        logger.debug(f"psutil temp failed: {e}")
    return None


def get_temperature() -> tuple[Optional[float], str]:
    """Try all strategies in priority order. Returns (value, source_label)."""
    t = _wmi_acpi_temp()
    if t is not None and 20 < t < 120:
        return t, "WMI MSAcpi_ThermalZone"
    t = _ohm_wmi_temp()
    if t is not None and 20 < t < 120:
        return t, "OpenHardwareMonitor WMI"
    t = _psutil_temp()
    if t is not None:
        return t, "psutil sensors"
    logger.warning(
        "CPU temp unavailable. Install LibreHardwareMonitor and enable WMI: "
        "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor"
    )
    return None, "unavailable – install LibreHardwareMonitor"


def get_top_processes(n: int = 10) -> List[dict]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "io_counters"]):
        try:
            info = p.info
            io = info.get("io_counters")
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu_pct": round(info["cpu_percent"] or 0, 1),
                "mem_pct": round(info["memory_percent"] or 0, 2),
                "io_read_mb": round(io.read_bytes / 1e6, 2) if io else 0,
                "io_write_mb": round(io.write_bytes / 1e6, 2) if io else 0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: x["cpu_pct"], reverse=True)[:n]


def collect(top_n: int = 10) -> CPUSnapshot:
    snap = CPUSnapshot()
    snap.total_pct = psutil.cpu_percent(interval=None)
    snap.per_core_pct = psutil.cpu_percent(interval=None, percpu=True)
    freqs = psutil.cpu_freq(percpu=True) or []
    snap.per_core_freq_mhz = [round(f.current, 1) for f in freqs]
    snap.temp_celsius, snap.temp_source = get_temperature()
    snap.top_processes = get_top_processes(top_n)
    return snap


def get_cpu_percent() -> float:
    """Wrapper function for API compatibility."""
    return psutil.cpu_percent(interval=None)
