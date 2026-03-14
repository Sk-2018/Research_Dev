import subprocess
import time

import psutil


def _parse_wmi_temp_output(output):
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            # WMI reports tenths of Kelvin.
            temp_k_tenths = float(line)
        except ValueError:
            continue
        return round((temp_k_tenths / 10.0) - 273.15, 1)
    return -1.0


def get_wmi_temperature():
    try:
        # Attempts to read WMI MSAcpi_ThermalZone via PowerShell.
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZone -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return _parse_wmi_temp_output(result.stdout)
    except Exception:
        return -1.0


def _get_top_processes(limit=3):
    procs = []
    process_list = []
    cpu_count = max(1, int(psutil.cpu_count(logical=True) or 1))
    for proc in psutil.process_iter(["name"]):
        try:
            proc.cpu_percent(interval=None)
            process_list.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Short sampling window for per-process CPU usage.
    time.sleep(0.1)
    for proc in process_list:
        try:
            name = proc.name() or f"pid:{proc.pid}"
            if name.strip().lower() == "system idle process":
                continue
            # Normalize process CPU from per-core scale to 0-100%.
            cpu = float(proc.cpu_percent(interval=None) or 0.0) / cpu_count
            procs.append({"name": name, "cpu": round(cpu, 1)})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    procs.sort(key=lambda p: p["cpu"], reverse=True)
    return procs[:limit]


def get_system_metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "ram_percent": psutil.virtual_memory().percent,
        "temp_c": get_wmi_temperature(),
        "top_processes": _get_top_processes(),
    }
