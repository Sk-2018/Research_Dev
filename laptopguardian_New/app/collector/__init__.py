from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.collector import battery, cpu, disk, gpu, memory, power


def collect_snapshot(top_n_processes: int = 10) -> dict[str, Any]:
    cpu_snapshot = cpu.collect(top_n=max(1, int(top_n_processes)))
    memory_snapshot = memory.collect()
    disk_snapshot = disk.collect()
    gpu_snapshot = gpu.collect()
    battery_snapshot = battery.collect()
    power_snapshot = power.collect()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cpu": asdict(cpu_snapshot),
        "memory": asdict(memory_snapshot),
        "disk": asdict(disk_snapshot),
        "gpu": asdict(gpu_snapshot),
        "battery": asdict(battery_snapshot),
        "power": asdict(power_snapshot),
    }


# Alias for scheduler compatibility
collect_all = collect_snapshot


__all__ = ["collect_snapshot", "collect_all"]
