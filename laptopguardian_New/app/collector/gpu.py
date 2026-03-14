"""
GPU collector for AMD Radeon (iGPU on Ryzen 7 5700U).
Tries WMI / DirectX DXGI path. Falls back gracefully.
Note: AMD iGPU telemetry via WMI is limited without AMD drivers exposing perf counters.
Recommended: Install LibreHardwareMonitor for better GPU metrics.
"""
import subprocess, logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GPUSnapshot:
    utilization_pct: Optional[float] = None
    source: str = "unavailable"
    note: str = ""


def _wmi_gpu_load() -> Optional[float]:
    ps = (
        "Get-WmiObject -Class Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine "
        "2>$null | Where-Object{$_.Name -like '*_engtype_3D*'} | "
        "Measure-Object -Property UtilizationPercentage -Maximum | "
        "Select-Object -ExpandProperty Maximum"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=8
        )
        val = r.stdout.strip()
        if val:
            return float(val)
    except Exception as e:
        logger.debug(f"GPU WMI failed: {e}")
    return None


def _ohm_gpu_temp() -> Optional[float]:
    ps = (
        "Get-WmiObject -Namespace root/OpenHardwareMonitor -Class Sensor "
        "2>$null | Where-Object{$_.SensorType -eq 'Load' -and $_.Name -like '*GPU*'} "
        "| Select-Object -First 1 -ExpandProperty Value"
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
        logger.debug(f"OHM GPU failed: {e}")
    return None


def collect() -> GPUSnapshot:
    snap = GPUSnapshot()
    val = _wmi_gpu_load()
    if val is not None:
        snap.utilization_pct = round(val, 1)
        snap.source = "WMI GPUEngine"
        return snap
    val = _ohm_gpu_temp()
    if val is not None:
        snap.utilization_pct = round(val, 1)
        snap.source = "OpenHardwareMonitor"
        return snap
    snap.note = (
        "AMD iGPU load unavailable via WMI on this config. "
        "Install LibreHardwareMonitor and enable WMI for GPU metrics."
    )
    return snap


def get_gpu_status() -> dict:
    """Wrapper function for API compatibility."""
    snap = collect()
    return {
        "gpu_name": snap.source,
        "gpu_percent": snap.utilization_pct or 0,
        "gpu_temp_c": 0,  # Not available from current implementation
    }
