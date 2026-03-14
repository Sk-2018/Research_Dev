from __future__ import annotations

import psutil


def get_disk_percent(path: str = "C:\\") -> float:
    try:
        return float(psutil.disk_usage(path).percent)
    except Exception:
        return 0.0
