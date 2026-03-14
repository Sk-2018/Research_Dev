from __future__ import annotations

import time
from typing import Any

import psutil


def get_cpu_percent(sample_seconds: float = 0.25) -> float:
    sample = max(0.1, float(sample_seconds))
    return float(psutil.cpu_percent(interval=sample))


def get_top_processes(limit: int = 10) -> list[dict[str, Any]]:
    process_list: list[psutil.Process] = []
    top: list[dict[str, Any]] = []
    max_items = max(1, int(limit))
    cpu_count = max(1, int(psutil.cpu_count(logical=True) or 1))

    for proc in psutil.process_iter(["name"]):
        try:
            proc.cpu_percent(interval=None)
            process_list.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Short warm-up so cpu_percent has meaningful delta.
    time.sleep(0.1)
    for proc in process_list:
        try:
            name = proc.name() or f"pid:{proc.pid}"
            if name.strip().lower() == "system idle process":
                continue
            cpu = float(proc.cpu_percent(interval=None) or 0.0) / cpu_count
            if cpu <= 0:
                continue
            top.append({"pid": int(proc.pid), "name": name, "cpu": round(cpu, 1)})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    top.sort(key=lambda row: row["cpu"], reverse=True)
    return top[:max_items]
