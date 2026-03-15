"""Unit tests for Jarvis schema validation and rule-based proposals."""
import unittest

from app.agent.jarvis import _rule_based_propose, propose, validate_action


BASE_CFG = {
    "thresholds": {
        "temp_warn": 75.0,
        "temp_critical": 88.0,
        "cpu_warn": 80.0,
        "cpu_critical": 95.0,
    },
    "ats": {
        "enabled": True,
        "maintenance_toast_threshold": 40.0,
        "script_path": "C:\\ATS_Maintenance_Aspire.bat",
    },
    "process_allowlist": {"priority_lower": ["node.exe"], "kill_candidates": ["node.exe"]},
}


def make_telemetry(cpu=20.0, temp=45.0):
    return {
        "cpu": {
            "total_pct": cpu,
            "temp_celsius": temp,
            "top_processes": [{"name": "node.exe", "pid": 1234, "cpu_pct": cpu, "mem_pct": 5.0, "io_read_mb": 0, "io_write_mb": 0}],
        },
        "memory": {"ram_pct": 40.0},
    }


class TestJarvisSchema(unittest.TestCase):
    def test_valid_schema(self) -> None:
        proposal = {
            "action": "no_action",
            "target": "system",
            "reason": "All good",
            "confidence": 0.99,
            "safety": {"requires_confirmation": False, "is_destructive": False},
        }
        self.assertTrue(validate_action(proposal))

    def test_invalid_action_enum(self) -> None:
        proposal = {
            "action": "destroy_everything",
            "target": "system",
            "reason": "nope",
            "confidence": 0.5,
            "safety": {"requires_confirmation": True},
        }
        self.assertFalse(validate_action(proposal))

    def test_confidence_out_of_range(self) -> None:
        proposal = {
            "action": "no_action",
            "target": "system",
            "reason": "ok",
            "confidence": 1.5,
            "safety": {"requires_confirmation": False},
        }
        self.assertFalse(validate_action(proposal))

    def test_rule_based_nominal(self) -> None:
        proposal = _rule_based_propose(make_telemetry(cpu=20, temp=45), BASE_CFG)
        self.assertEqual(proposal["action"], "no_action")
        self.assertTrue(validate_action(proposal))

    def test_rule_based_warn(self) -> None:
        proposal = _rule_based_propose(make_telemetry(cpu=85, temp=50), BASE_CFG)
        self.assertEqual(proposal["action"], "lower_priority")
        self.assertTrue(validate_action(proposal))

    def test_rule_based_critical(self) -> None:
        proposal = _rule_based_propose(make_telemetry(cpu=50, temp=90), BASE_CFG)
        self.assertEqual(proposal["action"], "propose_terminate")
        self.assertTrue(proposal["safety"]["requires_confirmation"])
        self.assertTrue(validate_action(proposal))

    def test_propose_recommends_maintenance_script_when_ats_score_high(self) -> None:
        ats_result = {
            "maintenance_score": 55.0,
            "verdict": "MAINTENANCE_NEEDED",
            "top_reasons": ["Temp directories total 1800 MB"],
        }
        proposal = propose(make_telemetry(cpu=20, temp=45), BASE_CFG, ats_result=ats_result)
        self.assertEqual(proposal["action"], "run_maintenance_script")
        self.assertTrue(proposal["safety"]["requires_confirmation"])
        self.assertTrue(validate_action(proposal))

    def test_thermal_actions_take_precedence_over_maintenance_recommendation(self) -> None:
        ats_result = {
            "maintenance_score": 90.0,
            "verdict": "CRITICAL_MAINTENANCE",
            "top_reasons": ["Disk space low"],
        }
        proposal = propose(make_telemetry(cpu=97, temp=92), BASE_CFG, ats_result=ats_result)
        self.assertEqual(proposal["action"], "propose_terminate")


if __name__ == "__main__":
    unittest.main()
