from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import Any

from app.collector.battery import get_battery_status
from app.collector.cpu import get_cpu_percent, get_top_processes
from app.collector.disk import get_disk_percent
from app.collector.gpu import get_gpu_status
from app.collector.memory import get_memory_percent


def _parse_wmi_temperature(output: str) -> float:
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            temp_k_tenths = float(line)
            return round((temp_k_tenths / 10.0) - 273.15, 1)
        except ValueError:
            continue
    return -1.0


def get_cpu_temperature() -> float:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZone -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return _parse_wmi_temperature(result.stdout or "")
    except Exception:
        return -1.0


def collect_snapshot(top_n_processes: int = 10) -> dict[str, Any]:
    battery = get_battery_status()
    gpu = get_gpu_status()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cpu_percent": get_cpu_percent(),
        "ram_percent": get_memory_percent(),
        "disk_percent": get_disk_percent(),
        "temp_c": get_cpu_temperature(),
        "battery_percent": battery["percent"],
        "battery_plugged": battery["plugged"],
        "gpu_name": gpu["gpu_name"],
        "gpu_percent": gpu["gpu_percent"],
        "gpu_temp_c": gpu["gpu_temp_c"],
        "top_processes": get_top_processes(limit=max(1, int(top_n_processes))),
    }


# Alias for scheduler compatibility
collect_all = collect_snapshot


__all__ = ["collect_snapshot", "collect_all", "get_cpu_temperature"]
