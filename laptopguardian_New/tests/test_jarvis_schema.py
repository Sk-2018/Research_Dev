import copy
import unittest

from app.agent.jarvis import ask_jarvis, normalize_decision, rule_based_decision
from app.configuration import DEFAULT_CONFIG


class TestJarvisSchema(unittest.TestCase):
    def setUp(self) -> None:
        self.config = copy.deepcopy(DEFAULT_CONFIG)

    def test_normalize_rejects_invalid_json(self) -> None:
        decision = normalize_decision("not-json")
        self.assertEqual(decision["action"], "NONE")
        self.assertIn("invalid", decision["reason"].lower())

    def test_normalize_accepts_valid_object(self) -> None:
        raw = {
            "action": "lower_priority",
            "target": "python.exe",
            "reason": "CPU spike",
            "safety": {"requires_confirmation": 0},
        }
        decision = normalize_decision(raw)
        self.assertEqual(decision["action"], "LOWER_PRIORITY")
        self.assertEqual(decision["target"], "python.exe")
        self.assertFalse(decision["safety"]["requires_confirmation"])

    def test_rule_decision_warn_prefers_allowlisted_process(self) -> None:
        snapshot = {
            "top_processes": [
                {"name": "unknown.exe", "cpu": 88.0},
                {"name": "python.exe", "cpu": 62.0},
            ]
        }
        assessment = {"risk_level": "warn", "risk_flags": ["cpu_warn_now"], "risk_score": 64}
        decision = rule_based_decision(snapshot, assessment, self.config)
        self.assertEqual(decision["action"], "LOWER_PRIORITY")
        self.assertEqual(decision["target"], "python.exe")

    def test_ask_jarvis_adds_accountability_meta(self) -> None:
        self.config["agent"]["enabled"] = True
        self.config["agent"]["use_llm"] = False
        snapshot = {"top_processes": [{"name": "python.exe", "cpu": 60.0}]}
        assessment = {"risk_level": "warn", "risk_flags": ["cpu_warn_now"], "risk_score": 62}
        decision = ask_jarvis(snapshot, assessment, self.config)
        self.assertIn("meta", decision)
        self.assertEqual(decision["meta"]["decision_source"], "rule_based_policy")
        self.assertFalse(decision["meta"]["llm_requested"])


if __name__ == "__main__":
    unittest.main()
