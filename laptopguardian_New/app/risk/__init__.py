from app.risk.scorer import RiskResult, TIER_CRITICAL, TIER_INFO, TIER_WARN, compute


def calculate_risk_score(telemetry: dict, cfg: dict) -> RiskResult:
    return compute(telemetry, cfg)


class RiskScorer:
    def compute(self, telemetry: dict, cfg: dict) -> RiskResult:
        return compute(telemetry, cfg)


__all__ = [
    "RiskScorer",
    "calculate_risk_score",
    "compute",
    "TIER_INFO",
    "TIER_WARN",
    "TIER_CRITICAL",
    "RiskResult",
]
