"""Unit tests for Jarvis schema validation and rule-based proposals."""
import pytest
from app.agent.jarvis import validate_action, _rule_based_propose

BASE_CFG = {
    "thresholds": {
        "temp_warn": 75.0, "temp_critical": 88.0,
        "cpu_warn": 80.0,  "cpu_critical": 95.0,
    },
    "process_allowlist": {"priority_lower": ["node.exe"], "kill_candidates": ["node.exe"]},
}


def make_telemetry(cpu=20.0, temp=45.0):
    return {
        "cpu": {"total_pct": cpu, "temp_celsius": temp,
                "top_processes": [{"name": "node.exe", "pid": 1234, "cpu_pct": cpu,
                                   "mem_pct": 5.0, "io_read_mb": 0, "io_write_mb": 0}]},
        "memory": {"ram_pct": 40.0},
    }


def test_valid_schema():
    proposal = {
        "action": "no_action", "target": "system",
        "reason": "All good", "confidence": 0.99,
        "safety": {"requires_confirmation": False, "is_destructive": False}
    }
    assert validate_action(proposal) is True


def test_invalid_action_enum():
    proposal = {
        "action": "destroy_everything", "target": "system",
        "reason": "nope", "confidence": 0.5,
        "safety": {"requires_confirmation": True}
    }
    assert validate_action(proposal) is False


def test_confidence_out_of_range():
    proposal = {
        "action": "no_action", "target": "system",
        "reason": "ok", "confidence": 1.5,
        "safety": {"requires_confirmation": False}
    }
    assert validate_action(proposal) is False


def test_rule_based_nominal():
    p = _rule_based_propose(make_telemetry(cpu=20, temp=45), BASE_CFG)
    assert p["action"] == "no_action"
    assert validate_action(p) is True


def test_rule_based_warn():
    p = _rule_based_propose(make_telemetry(cpu=85, temp=50), BASE_CFG)
    assert p["action"] == "lower_priority"
    assert validate_action(p) is True


def test_rule_based_critical():
    p = _rule_based_propose(make_telemetry(cpu=50, temp=90), BASE_CFG)
    assert p["action"] == "propose_terminate"
    assert p["safety"]["requires_confirmation"] is True
    assert validate_action(p) is True
