"""Unit tests for the risk scorer."""
import pytest
from app.risk.scorer import compute, TIER_INFO, TIER_WARN, TIER_CRITICAL

BASE_CFG = {
    "thresholds": {
        "temp_warn": 75.0, "temp_critical": 88.0,
        "cpu_warn": 80.0,  "cpu_critical": 95.0,
        "ram_warn": 85.0,  "ram_critical": 95.0,
        "temp_slope_warn": 3.0, "temp_slope_critical": 6.0,
    },
    "risk_weights": {
        "temp_abs": 0.40, "temp_slope": 0.25,
        "cpu_sustained": 0.25, "ram_pressure": 0.10,
    }
}


def make_telemetry(cpu=20.0, temp=45.0, ram=40.0):
    return {
        "timestamp": 0,
        "cpu": {"total_pct": cpu, "temp_celsius": temp, "top_processes": []},
        "memory": {"ram_pct": ram},
        "disk": {}, "gpu": {}, "battery": {}, "power": {},
    }


def test_nominal():
    r = compute(make_telemetry(cpu=20, temp=45, ram=40), BASE_CFG)
    assert r.tier == TIER_INFO
    assert r.score < 40


def test_warn_on_high_temp():
    r = compute(make_telemetry(cpu=30, temp=78, ram=50), BASE_CFG)
    assert r.tier in (TIER_WARN, TIER_CRITICAL)


def test_critical_on_extreme():
    r = compute(make_telemetry(cpu=97, temp=92, ram=96), BASE_CFG)
    assert r.tier == TIER_CRITICAL
    assert r.score >= 70


def test_no_temp_fallback():
    t = make_telemetry()
    t["cpu"]["temp_celsius"] = None
    r = compute(t, BASE_CFG)
    assert r.tier == TIER_INFO


def test_score_range():
    r = compute(make_telemetry(cpu=100, temp=100, ram=100), BASE_CFG)
    assert 0 <= r.score <= 100


def test_reason_populated():
    r = compute(make_telemetry(cpu=97, temp=92, ram=40), BASE_CFG)
    assert len(r.reason) > 0
