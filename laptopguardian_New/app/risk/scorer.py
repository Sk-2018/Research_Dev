from __future__ import annotations

from collections import deque
from typing import Any


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _ratio(value: float, warn: float, critical: float) -> float:
    if value < 0:
        return 0.0
    if critical <= warn:
        return 1.0 if value > warn else 0.0
    if value <= warn:
        return 0.0
    return _clamp((value - warn) / (critical - warn), 0.0, 1.0)


class RiskScorer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._sample_interval_s = max(1.0, _safe_float(config["general"].get("sample_interval_seconds"), 3.0))
        self._temp_history = deque(maxlen=40)
        self._cpu_history = deque(maxlen=20)

    def _temperature_slope_c_per_min(self) -> float:
        if len(self._temp_history) < 2:
            return 0.0
        first = self._temp_history[0]
        last = self._temp_history[-1]
        points_between = max(1, len(self._temp_history) - 1)
        elapsed_minutes = (points_between * self._sample_interval_s) / 60.0
        if elapsed_minutes <= 0:
            return 0.0
        return (last - first) / elapsed_minutes

    def evaluate(self, metrics: dict[str, Any]) -> dict[str, Any]:
        thresholds = self.config["thresholds"]
        weights = self.config["risk_weights"]

        temp_c = _safe_float(metrics.get("temp_c"), -1.0)
        cpu_percent = _safe_float(metrics.get("cpu_percent"), 0.0)
        ram_percent = _safe_float(metrics.get("ram_percent"), 0.0)

        if temp_c > 0:
            self._temp_history.append(temp_c)
        self._cpu_history.append(cpu_percent)

        temp_slope = self._temperature_slope_c_per_min()
        cpu_avg = sum(self._cpu_history) / max(1, len(self._cpu_history))

        temp_abs_component = _ratio(temp_c, _safe_float(thresholds["temp_warn"]), _safe_float(thresholds["temp_critical"]))
        temp_slope_component = _ratio(
            temp_slope,
            _safe_float(thresholds["temp_slope_warn"]),
            _safe_float(thresholds["temp_slope_critical"]),
        )
        cpu_component = _ratio(cpu_avg, _safe_float(thresholds["cpu_warn"]), _safe_float(thresholds["cpu_critical"]))
        ram_component = _ratio(ram_percent, _safe_float(thresholds["ram_warn"]), _safe_float(thresholds["ram_critical"]))

        weighted_score = (
            temp_abs_component * _safe_float(weights["temp_abs"])
            + temp_slope_component * _safe_float(weights["temp_slope"])
            + cpu_component * _safe_float(weights["cpu_sustained"])
            + ram_component * _safe_float(weights["ram_pressure"])
        )
        risk_score = int(round(_clamp(weighted_score * 100.0, 0.0, 100.0)))

        flags: list[str] = []
        if temp_c < 0:
            flags.append("temperature_unavailable")
        else:
            if temp_c >= _safe_float(thresholds["temp_critical"]):
                flags.append("temp_critical")
            elif temp_c >= _safe_float(thresholds["temp_warn"]):
                flags.append("temp_warn")

        if cpu_percent >= _safe_float(thresholds["cpu_critical"]):
            flags.append("cpu_critical_now")
        elif cpu_percent >= _safe_float(thresholds["cpu_warn"]):
            flags.append("cpu_warn_now")

        if cpu_avg >= _safe_float(thresholds["cpu_critical"]):
            flags.append("cpu_critical_sustained")
        elif cpu_avg >= _safe_float(thresholds["cpu_warn"]):
            flags.append("cpu_warn_sustained")

        if ram_percent >= _safe_float(thresholds["ram_critical"]):
            flags.append("ram_critical")
        elif ram_percent >= _safe_float(thresholds["ram_warn"]):
            flags.append("ram_warn")

        if temp_slope >= _safe_float(thresholds["temp_slope_critical"]):
            flags.append("temp_slope_critical")
        elif temp_slope >= _safe_float(thresholds["temp_slope_warn"]):
            flags.append("temp_slope_warn")

        if any(flag.endswith("critical") or "critical_" in flag for flag in flags) or risk_score >= 85:
            risk_level = "critical"
        elif any(flag.endswith("warn") or "warn_" in flag for flag in flags) or risk_score >= 55:
            risk_level = "warn"
        else:
            risk_level = "normal"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_flags": flags,
            "temp_slope_c_per_min": round(temp_slope, 2),
            "cpu_avg_percent": round(cpu_avg, 2),
        }


def calculate_risk_score(metrics: dict[str, Any], config: dict[str, Any]) -> int:
    scorer = RiskScorer(config)
    return int(scorer.evaluate(metrics)["risk_score"])

# ===== Scheduler Compatibility Wrappers =====
from dataclasses import dataclass

TIER_INFO     = "normal"
TIER_WARN     = "warn"
TIER_CRITICAL = "critical"


@dataclass
class RiskResult:
    """Wrapper result object for scheduler compatibility."""
    score: float
    tier: str
    reason: str = ""


def compute(telemetry: dict[str, Any], cfg: dict[str, Any]) -> RiskResult:
    """Compatibility wrapper that converts new scorer to old API."""
    # Extract metrics from telemetry dict
    metrics = {
        "temp_c": telemetry.get("temp_c", -1.0),
        "cpu_percent": telemetry.get("cpu_percent", 0.0),
        "ram_percent": telemetry.get("ram_percent", 0.0),
    }
    
    # Run the new scorer
    scorer = RiskScorer(cfg)
    result = scorer.evaluate(metrics)
    
    # Map new format to old format
    scored_return = RiskResult(
        score=float(result["risk_score"]),
        tier=result["risk_level"],
        reason=", ".join(result.get("risk_flags", [])) or "System nominal"
    )
    return scored_return
