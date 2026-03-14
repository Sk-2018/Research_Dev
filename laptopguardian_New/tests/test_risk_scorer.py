import copy
import unittest

from app.configuration import DEFAULT_CONFIG
from app.risk.scorer import RiskScorer, compute


class TestRiskScorer(unittest.TestCase):
    def setUp(self) -> None:
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.config["general"]["sample_interval_seconds"] = 2

    def test_low_utilization_stays_normal(self) -> None:
        scorer = RiskScorer(self.config)
        assessment = scorer.evaluate(
            {
                "cpu_percent": 20.0,
                "ram_percent": 40.0,
                "temp_c": 50.0,
                "top_processes": [],
            }
        )
        self.assertEqual(assessment["risk_level"], "normal")
        self.assertLess(assessment["risk_score"], 35)

    def test_critical_pressure_becomes_critical(self) -> None:
        scorer = RiskScorer(self.config)
        assessment = {}
        for temp in [78.0, 82.0, 88.5]:
            assessment = scorer.evaluate(
                {
                    "cpu_percent": 97.0,
                    "ram_percent": 96.0,
                    "temp_c": temp,
                    "top_processes": [{"name": "python.exe", "cpu": 70.0}],
                }
            )

        self.assertEqual(assessment["risk_level"], "critical")
        self.assertGreaterEqual(assessment["risk_score"], 80)
        self.assertTrue(any("critical" in flag for flag in assessment["risk_flags"]))

    def test_first_high_cpu_sample_is_not_marked_sustained(self) -> None:
        scorer = RiskScorer(self.config)
        assessment = scorer.evaluate(
            {
                "cpu_percent": 96.0,
                "ram_percent": 40.0,
                "temp_c": 50.0,
                "top_processes": [],
            }
        )
        self.assertIn("cpu_critical_now", assessment["risk_flags"])
        self.assertNotIn("cpu_critical_sustained", assessment["risk_flags"])

    def test_compute_wrapper_preserves_scorer_history(self) -> None:
        result = None
        for temp in [60.0, 61.0, 62.0]:
            result = compute(
                {
                    "cpu_percent": 20.0,
                    "ram_percent": 40.0,
                    "temp_c": temp,
                    "top_processes": [],
                },
                self.config,
            )

        self.assertIsNotNone(result)
        self.assertEqual(result.tier, "critical")
        self.assertIn("temp_slope_critical", result.reason)


if __name__ == "__main__":
    unittest.main()
