
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
