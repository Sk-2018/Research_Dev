from __future__ import annotations

import re
import subprocess
from typing import Optional


POWER_SAVER_GUID = "a1841308-3541-4fab-bc81-f71556f20b4a"
BALANCED_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"


def _run_powercfg(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powercfg", *args],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def get_active_plan_guid() -> Optional[str]:
    result = _run_powercfg(["/getactivescheme"])
    if result.returncode != 0:
        return None
    output = (result.stdout or "").strip()
    match = re.search(r"([0-9a-fA-F-]{36})", output)
    if not match:
        return None
    return match.group(1).lower()


def set_active_plan(plan_guid: str) -> tuple[bool, str]:
    result = _run_powercfg(["/setactive", plan_guid])
    if result.returncode == 0:
        return True, ""
    error = (result.stderr or result.stdout or "").strip()
    return False, error
