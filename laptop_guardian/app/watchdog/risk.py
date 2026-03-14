from collections import deque


class RiskEngine:
    def __init__(self, config):
        self.config = config
        self._cpu_history = deque(maxlen=12)
        self._temp_history = deque(maxlen=12)

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def evaluate(self, metrics):
        thresholds = self.config["thresholds"]
        temp = self._safe_float(metrics.get("temp_c"), -1.0)
        cpu = self._safe_float(metrics.get("cpu_percent"), 0.0)
        ram = self._safe_float(metrics.get("ram_percent"), 0.0)

        self._cpu_history.append(cpu)
        if temp > 0:
            self._temp_history.append(temp)

        score = 0
        reasons = []

        if temp > 0:
            if temp >= thresholds["temp_critical"]:
                score += 65
                reasons.append("temperature_critical")
            elif temp >= thresholds["temp_warn"]:
                score += 35
                reasons.append("temperature_warn")
        else:
            reasons.append("temperature_unavailable")

        cpu_avg = sum(self._cpu_history) / max(1, len(self._cpu_history))
        if cpu >= thresholds["cpu_sustained_warn"]:
            score += 30
            reasons.append("cpu_high_now")
        elif cpu >= 70:
            score += 15
            reasons.append("cpu_moderate")

        if cpu_avg >= thresholds["cpu_sustained_warn"]:
            score += 20
            reasons.append("cpu_sustained_high")
        elif temp <= 0 and cpu_avg >= 70:
            score += 20
            reasons.append("cpu_proxy_heat")

        if ram >= 90:
            score += 10
            reasons.append("ram_high")

        if len(self._temp_history) >= 3:
            recent = list(self._temp_history)[-3:]
            if recent[-1] - recent[0] >= 3.0:
                score += 10
                reasons.append("temp_rising_fast")

        return min(100, int(round(score))), reasons


def calculate_risk_score(metrics, config):
    # Compatibility helper for legacy callers.
    engine = RiskEngine(config)
    score, _ = engine.evaluate(metrics)
    return score
