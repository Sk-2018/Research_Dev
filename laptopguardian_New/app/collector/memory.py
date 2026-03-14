"""RAM and pagefile/commit metrics."""
import psutil, subprocess, logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    ram_pct: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    pagefile_pct: Optional[float] = None
    commit_total_gb: Optional[float] = None
    commit_limit_gb: Optional[float] = None


def _wmi_pagefile() -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Returns (pagefile_pct, commit_total_gb, commit_limit_gb)."""
    ps = (
        "$os = Get-WmiObject Win32_OperatingSystem 2>$null; "
        "if($os){[PSCustomObject]@{"
        "CommitTotal=[math]::Round($os.TotalVirtualMemorySize/1MB,2);"
        "CommitLimit=[math]::Round(($os.TotalVirtualMemorySize + $os.TotalVisibleMemorySize)/1MB,2);"
        "PageUsePct=[math]::Round(100*($os.TotalVirtualMemorySize - $os.FreeVirtualMemory)/$os.TotalVirtualMemorySize,1)"
        "}|ConvertTo-Json}"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=6
        )
        import json
        d = json.loads(r.stdout.strip())
        return d.get("PageUsePct"), d.get("CommitTotal"), d.get("CommitLimit")
    except Exception as e:
        logger.debug(f"WMI pagefile query failed: {e}")
    return None, None, None


def collect() -> MemorySnapshot:
    vm = psutil.virtual_memory()
    snap = MemorySnapshot(
        ram_pct=vm.percent,
        ram_used_gb=round(vm.used / 1e9, 2),
        ram_total_gb=round(vm.total / 1e9, 2),
    )
    pct, total, limit = _wmi_pagefile()
    snap.pagefile_pct = pct
    snap.commit_total_gb = total
    snap.commit_limit_gb = limit
    return snap


def get_memory_percent() -> float:
    """Wrapper function for API compatibility."""
    vm = psutil.virtual_memory()
    return vm.percent
