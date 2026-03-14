from __future__ import annotations

import glob
import logging
import os
import re
import shutil
import subprocess
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class ATSSignal:
    name: str
    value: float
    unit: str
    status: str
    reason: str = ""
    score_contrib: float = 0.0


@dataclass
class ATSEvalResult:
    maintenance_score: float = 0.0
    verdict: str = "CLEAN"
    signals: list[ATSSignal] = field(default_factory=list)
    top_reasons: list[str] = field(default_factory=list)
    last_evaluated: float = 0.0
    fresh_scan: bool = False


DISK_FREE_WARN_GB = 30.0
DISK_FREE_CRIT_GB = 15.0
TEMP_DIR_WARN_MB = 500.0
TEMP_DIR_CRIT_MB = 1500.0
BROWSER_CACHE_WARN_MB = 800.0
BROWSER_CACHE_CRIT_MB = 2000.0
VHDX_WARN_GB = 15.0
VHDX_CRIT_GB = 22.0
WU_CACHE_WARN_MB = 500.0
WU_CACHE_CRIT_MB = 2000.0
DNS_WARN_MS = 80.0
DNS_CRIT_MS = 200.0
PING_LOSS_WARN_PCT = 5.0
PING_LOSS_CRIT_PCT = 20.0
TEMP_TREND_WARN_C_PER_MIN = 3.0
TEMP_TREND_CRIT_C_PER_MIN = 6.0

_last_static_eval_at = 0.0
_last_static_signals: list[ATSSignal] = []
_last_result = ATSEvalResult()
_temp_history: deque[tuple[float, float]] = deque(maxlen=60)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _dir_size_mb(path: str) -> float:
    total = 0
    try:
        for dirpath, _, files in os.walk(path):
            for filename in files:
                file_path = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(file_path)
                except OSError:
                    continue
    except Exception:
        return 0.0
    return round(total / 1_000_000.0, 1)


def _score(value: float, warn: float, crit: float, *, invert: bool = False) -> float:
    if invert:
        value, warn, crit = -value, -warn, -crit
    if value <= warn:
        return 0.0
    if value >= crit:
        return 1.0
    return (value - warn) / max(0.0001, crit - warn)


def _status(score: float) -> str:
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.35:
        return "WARN"
    return "OK"


def _record_temp_sample(telemetry: dict[str, Any]) -> None:
    temp_c = _safe_float(telemetry.get("temp_c"), -1.0)
    if temp_c <= 0:
        return
    _temp_history.append((time.time(), temp_c))


def _temperature_trend_signal(config: dict[str, Any] | None = None) -> ATSSignal:
    thresholds = (config or {}).get("thresholds", {})
    warn = _safe_float(thresholds.get("temp_slope_warn"), TEMP_TREND_WARN_C_PER_MIN)
    critical = _safe_float(thresholds.get("temp_slope_critical"), TEMP_TREND_CRIT_C_PER_MIN)
    if len(_temp_history) < 2:
        return ATSSignal("CPU Temp Trend", 0.0, "C/min", "OK", reason="", score_contrib=0.0)

    first_time, first_temp = _temp_history[0]
    last_time, last_temp = _temp_history[-1]
    elapsed_minutes = max(0.001, (last_time - first_time) / 60.0)
    slope = (last_temp - first_temp) / elapsed_minutes
    score = _score(slope, warn, critical)
    return ATSSignal(
        name="CPU Temp Trend",
        value=round(slope, 2),
        unit="C/min",
        status=_status(score),
        reason=f"CPU temperature rising at {slope:.1f} C/min" if score > 0 else "",
        score_contrib=score * 10.0,
    )


def check_disk_free() -> ATSSignal:
    try:
        usage = shutil.disk_usage("C:\\")
        free_gb = round(usage.free / 1_000_000_000.0, 2)
        score = _score(free_gb, DISK_FREE_WARN_GB, DISK_FREE_CRIT_GB, invert=True)
        return ATSSignal(
            name="Disk Free (C:)",
            value=free_gb,
            unit="GB",
            status=_status(score),
            reason=f"Only {free_gb:.1f} GB free on C:\\" if score > 0 else "",
            score_contrib=score * 30.0,
        )
    except Exception as exc:
        logger.debug("ATS disk check failed: %s", exc)
        return ATSSignal("Disk Free (C:)", 0.0, "GB", "OK", "", 0.0)


def check_temp_size() -> ATSSignal:
    temp_path = os.environ.get("TEMP", "C:\\Windows\\Temp")
    windows_temp = "C:\\Windows\\Temp"
    size_mb = _dir_size_mb(temp_path) + _dir_size_mb(windows_temp)
    score = _score(size_mb, TEMP_DIR_WARN_MB, TEMP_DIR_CRIT_MB)
    return ATSSignal(
        name="Temp Folder Size",
        value=round(size_mb, 1),
        unit="MB",
        status=_status(score),
        reason=f"Temp directories total {size_mb:.0f} MB" if score > 0 else "",
        score_contrib=score * 15.0,
    )


def check_browser_cache() -> ATSSignal:
    paths: list[str] = []
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")

    chrome_base = os.path.join(local, "Google", "Chrome", "User Data")
    if os.path.exists(chrome_base):
        for profile in glob.glob(os.path.join(chrome_base, "*")):
            for subdir in ("Cache", "Code Cache", "GPUCache"):
                candidate = os.path.join(profile, subdir)
                if os.path.exists(candidate):
                    paths.append(candidate)

    edge_base = os.path.join(local, "Microsoft", "Edge", "User Data")
    if os.path.exists(edge_base):
        for profile in glob.glob(os.path.join(edge_base, "*")):
            for subdir in ("Cache", "Code Cache", "GPUCache"):
                candidate = os.path.join(profile, subdir)
                if os.path.exists(candidate):
                    paths.append(candidate)

    firefox_base = os.path.join(roaming, "Mozilla", "Firefox", "Profiles")
    if os.path.exists(firefox_base):
        for profile in glob.glob(os.path.join(firefox_base, "*")):
            for subdir in ("cache2", "offlineCache", "startupCache"):
                candidate = os.path.join(profile, subdir)
                if os.path.exists(candidate):
                    paths.append(candidate)

    total_mb = sum(_dir_size_mb(path) for path in paths)
    score = _score(total_mb, BROWSER_CACHE_WARN_MB, BROWSER_CACHE_CRIT_MB)
    return ATSSignal(
        name="Browser Cache",
        value=round(total_mb, 1),
        unit="MB",
        status=_status(score),
        reason=f"Browser caches total {total_mb:.0f} MB" if score > 0 else "",
        score_contrib=score * 15.0,
    )


def check_docker_vhdx() -> ATSSignal:
    local = os.environ.get("LOCALAPPDATA", "")
    vhdx_path = os.path.join(local, "Docker", "wsl", "disk", "docker_data.vhdx")
    if not os.path.exists(vhdx_path):
        return ATSSignal("Docker VHDX", 0.0, "GB", "OK", "Docker VHDX not found", 0.0)

    try:
        size_gb = round(os.path.getsize(vhdx_path) / 1_000_000_000.0, 2)
        score = _score(size_gb, VHDX_WARN_GB, VHDX_CRIT_GB)
        return ATSSignal(
            name="Docker VHDX",
            value=size_gb,
            unit="GB",
            status=_status(score),
            reason=f"docker_data.vhdx is {size_gb:.1f} GB" if score > 0 else "",
            score_contrib=score * 20.0,
        )
    except OSError as exc:
        logger.debug("ATS Docker VHDX check failed: %s", exc)
        return ATSSignal("Docker VHDX", 0.0, "GB", "OK", "", 0.0)


def check_windows_update_cache() -> ATSSignal:
    cache_path = "C:\\Windows\\SoftwareDistribution\\Download"
    size_mb = _dir_size_mb(cache_path)
    score = _score(size_mb, WU_CACHE_WARN_MB, WU_CACHE_CRIT_MB)
    return ATSSignal(
        name="Windows Update Cache",
        value=round(size_mb, 1),
        unit="MB",
        status=_status(score),
        reason=f"Windows Update cache is {size_mb:.0f} MB" if score > 0 else "",
        score_contrib=score * 10.0,
    )


def check_dns_latency() -> ATSSignal:
    try:
        started = time.monotonic()
        subprocess.run(
            ["nslookup", "google.com"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        elapsed_ms = (time.monotonic() - started) * 1000.0
        score = _score(elapsed_ms, DNS_WARN_MS, DNS_CRIT_MS)
        return ATSSignal(
            name="DNS Latency",
            value=round(elapsed_ms, 1),
            unit="ms",
            status=_status(score),
            reason=f"DNS resolution slow: {elapsed_ms:.0f} ms" if score > 0 else "",
            score_contrib=score * 5.0,
        )
    except Exception as exc:
        logger.debug("ATS DNS check failed: %s", exc)
        return ATSSignal("DNS Latency", 0.0, "ms", "OK", "", 0.0)


def check_network_packet_loss() -> ATSSignal:
    try:
        result = subprocess.run(
            ["ping", "-n", "6", "8.8.8.8"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        match = re.search(r"Lost\s*=\s*\d+\s*\((\d+)%\s*loss\)", result.stdout or "", re.IGNORECASE)
        loss_pct = float(match.group(1)) if match else 0.0
        score = _score(loss_pct, PING_LOSS_WARN_PCT, PING_LOSS_CRIT_PCT)
        return ATSSignal(
            name="Packet Loss",
            value=round(loss_pct, 1),
            unit="%",
            status=_status(score),
            reason=f"Network packet loss {loss_pct:.0f}%" if score > 0 else "",
            score_contrib=score * 5.0,
        )
    except Exception as exc:
        logger.debug("ATS ping check failed: %s", exc)
        return ATSSignal("Packet Loss", 0.0, "%", "OK", "", 0.0)


def _heavy_signals() -> list[ATSSignal]:
    return [
        check_disk_free(),
        check_temp_size(),
        check_browser_cache(),
        check_docker_vhdx(),
        check_windows_update_cache(),
        check_dns_latency(),
        check_network_packet_loss(),
    ]


def _verdict(score: float) -> str:
    if score >= 70.0:
        return "CRITICAL_MAINTENANCE"
    if score >= 40.0:
        return "MAINTENANCE_NEEDED"
    if score >= 20.0:
        return "ADVISORY"
    return "CLEAN"


def get_latest_result() -> ATSEvalResult:
    return _last_result


def evaluate(telemetry: dict[str, Any], config: dict[str, Any] | None = None, *, force: bool = False) -> ATSEvalResult:
    global _last_static_eval_at, _last_static_signals, _last_result

    _record_temp_sample(telemetry)
    ats_cfg = (config or {}).get("ats", {})
    interval_seconds = max(10, int(ats_cfg.get("evaluation_interval_seconds", 120)))
    now = time.time()
    fresh_scan = False

    if force or not _last_static_signals or (now - _last_static_eval_at) >= interval_seconds:
        _last_static_signals = _heavy_signals()
        _last_static_eval_at = now
        fresh_scan = True

    signals = list(_last_static_signals)
    signals.append(_temperature_trend_signal(config))
    total_score = min(100.0, sum(signal.score_contrib for signal in signals))
    top_reasons = [
        signal.reason
        for signal in sorted(signals, key=lambda item: item.score_contrib, reverse=True)
        if signal.reason
    ]

    _last_result = ATSEvalResult(
        maintenance_score=round(total_score, 1),
        verdict=_verdict(total_score),
        signals=signals,
        top_reasons=top_reasons,
        last_evaluated=now,
        fresh_scan=fresh_scan,
    )
    if fresh_scan:
        logger.info(
            "ATS evaluation score=%.1f verdict=%s fresh_scan=%s",
            _last_result.maintenance_score,
            _last_result.verdict,
            _last_result.fresh_scan,
        )
    return _last_result
