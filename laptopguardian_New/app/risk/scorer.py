"""
Thermal Risk Scorer.
Produces a 0-100 score and an alert tier: INFO / WARN / CRITICAL.
Uses a sliding window of recent temp readings to compute slope (°C/min).
"""
import time, collections, logging
from dataclasses import dataclass
from typing import Optional, Deque

logger = logging.getLogger(__name__)

TIER_INFO     = "INFO"
TIER_WARN     = "WARN"
TIER_CRITICAL = "CRITICAL"

# Sliding window: (timestamp, temp_c) tuples
_temp_history: Deque = collections.deque(maxlen=60)   # ~3 min at 3s interval


@dataclass
class RiskResult:
    score: float = 0.0          # 0–100
    tier: str = TIER_INFO
    temp_slope_per_min: float = 0.0
    components: dict = None
    reason: str = ""


def _compute_slope() -> float:
    """Linear regression slope of recent temperatures in °C/min."""
    if len(_temp_history) < 4:
        return 0.0
    xs = [t for t, _ in _temp_history]
    ys = [v for _, v in _temp_history]
    x0 = xs[0]
    xs = [x - x0 for x in xs]
    n = len(xs)
    sx, sy, sxy, sx2 = sum(xs), sum(ys), sum(a*b for a,b in zip(xs,ys)), sum(a**2 for a in xs)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0.0
    slope_per_sec = (n * sxy - sx * sy) / denom
    return slope_per_sec * 60.0   # °C per minute


def compute(telemetry: dict, cfg: dict) -> RiskResult:
    thresholds = cfg.get("thresholds", {})
    weights    = cfg.get("risk_weights", {})

    temp_warn     = thresholds.get("temp_warn",        75.0)
    temp_crit     = thresholds.get("temp_critical",    88.0)
    cpu_warn      = thresholds.get("cpu_warn",         80.0)
    cpu_crit      = thresholds.get("cpu_critical",     95.0)
    ram_warn      = thresholds.get("ram_warn",         85.0)
    ram_crit      = thresholds.get("ram_critical",     95.0)
    slope_warn    = thresholds.get("temp_slope_warn",   3.0)
    slope_crit    = thresholds.get("temp_slope_critical", 6.0)

    w_temp   = weights.get("temp_abs",       0.40)
    w_slope  = weights.get("temp_slope",     0.25)
    w_cpu    = weights.get("cpu_sustained",  0.25)
    w_ram    = weights.get("ram_pressure",   0.10)

    cpu_pct  = telemetry.get("cpu", {}).get("total_pct", 0.0)
    temp_c   = telemetry.get("cpu", {}).get("temp_celsius")
    ram_pct  = telemetry.get("memory", {}).get("ram_pct", 0.0)

    # Update sliding window
    if temp_c is not None:
        _temp_history.append((time.monotonic(), temp_c))

    slope = _compute_slope()

    # Normalise each component to 0-1
    def norm(val, warn, crit):
        if val <= warn:
            return (val / warn) * 0.5 if warn > 0 else 0
        elif val >= crit:
            return 1.0
        else:
            return 0.5 + 0.5 * (val - warn) / (crit - warn)

    temp_norm  = norm(temp_c or 0, temp_warn, temp_crit)
    slope_norm = norm(abs(slope), slope_warn, slope_crit)
    cpu_norm   = norm(cpu_pct,  cpu_warn,  cpu_crit)
    ram_norm   = norm(ram_pct,  ram_warn,  ram_crit)

    score = (
        w_temp  * temp_norm  +
        w_slope * slope_norm +
        w_cpu   * cpu_norm   +
        w_ram   * ram_norm
    ) * 100.0
    score = min(100.0, round(score, 1))

    # Tier
    if score >= 70 or (temp_c or 0) >= temp_crit or cpu_pct >= cpu_crit:
        tier = TIER_CRITICAL
    elif score >= 40 or (temp_c or 0) >= temp_warn or cpu_pct >= cpu_warn:
        tier = TIER_WARN
    else:
        tier = TIER_INFO

    reasons = []
    if temp_c is not None and temp_c >= temp_warn:
        reasons.append(f"Temp {temp_c:.1f}°C")
    if slope > slope_warn:
        reasons.append(f"Temp rising {slope:.1f}°C/min")
    if cpu_pct >= cpu_warn:
        reasons.append(f"CPU {cpu_pct:.0f}%")
    if ram_pct >= ram_warn:
        reasons.append(f"RAM {ram_pct:.0f}%")

    return RiskResult(
        score=score,
        tier=tier,
        temp_slope_per_min=round(slope, 2),
        components={
            "temp_norm": round(temp_norm, 3),
            "slope_norm": round(slope_norm, 3),
            "cpu_norm": round(cpu_norm, 3),
            "ram_norm": round(ram_norm, 3),
        },
        reason=", ".join(reasons) if reasons else "System nominal",
    )
