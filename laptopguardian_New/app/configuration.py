from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "general": {
        "sample_interval_seconds": 3,
        "log_retention_days": 7,
        "db_path": "guardian.db",
        "log_path": "logs/guardian.log",
        "dry_run": False,
        "top_n_processes": 10,
    },
    "dashboard": {
        "host": "127.0.0.1",
        "port": 8050,
        "chart_window_minutes": 30,
    },
    "thresholds": {
        "temp_warn": 75.0,
        "temp_critical": 88.0,
        "cpu_warn": 80.0,
        "cpu_critical": 95.0,
        "ram_warn": 85.0,
        "ram_critical": 95.0,
        "temp_slope_warn": 3.0,
        "temp_slope_critical": 6.0,
    },
    "risk_weights": {
        "temp_abs": 0.40,
        "temp_slope": 0.25,
        "cpu_sustained": 0.25,
        "ram_pressure": 0.10,
    },
    "actions": {
        "switch_power_saver_on_warn": True,
        "restore_power_plan_on_cool": True,
        "lower_process_priority_on_warn": True,
        "toast_on_critical": True,
        "suspend_workloads_on_critical": False,
    },
    "process_allowlist": {
        "priority_lower": ["node.exe", "python.exe", "docker.exe", "java.exe", "code.exe"],
        "kill_candidates": ["node.exe", "python.exe", "java.exe"],
    },
    "agent": {
        "enabled": False,
        "use_llm": False,
        "ollama_url": "http://localhost:11434/api/generate",
        "ollama_model": "mistral",
        "rule_based_fallback": True,
    },
    "accountability": {
        "policy_version": "2026-03-01",
        "record_noop_decisions": True,
        "allow_destructive_actions": False,
        "block_unconfirmed_actions": True,
    },
    "ats": {
        "enabled": True,
        "evaluation_interval_seconds": 120,
        "toast_cooldown_seconds": 1800,
        "maintenance_toast_threshold": 40.0,
        "script_path": "..\\ATS_Maintenance_Aspire.bat",
    },
    "event_log": {
        "enabled": True,
        "look_back_hours": 24,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _normalize_process_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("process lists must be arrays in config.yaml")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        name = str(item).strip()
        if not name:
            continue
        lowered = name.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(name)
    return cleaned


def validate_config(config: dict[str, Any]) -> None:
    general = config["general"]
    dashboard = config["dashboard"]
    thresholds = config["thresholds"]
    weights = config["risk_weights"]
    actions = config["actions"]
    allowlist = config["process_allowlist"]
    agent = config["agent"]
    accountability = config["accountability"]
    ats = config["ats"]
    event_log = config["event_log"]

    _require(float(general["sample_interval_seconds"]) >= 1, "general.sample_interval_seconds must be >= 1")
    _require(int(general["log_retention_days"]) >= 1, "general.log_retention_days must be >= 1")
    _require(int(general["top_n_processes"]) >= 1, "general.top_n_processes must be >= 1")
    _require(1 <= int(dashboard["port"]) <= 65535, "dashboard.port must be 1-65535")
    _require(float(dashboard["chart_window_minutes"]) >= 1, "dashboard.chart_window_minutes must be >= 1")

    _require(float(thresholds["temp_warn"]) > 0, "thresholds.temp_warn must be > 0")
    _require(float(thresholds["temp_critical"]) > float(thresholds["temp_warn"]), "temp_critical must be > temp_warn")
    _require(0 <= float(thresholds["cpu_warn"]) < float(thresholds["cpu_critical"]) <= 100, "invalid cpu thresholds")
    _require(0 <= float(thresholds["ram_warn"]) < float(thresholds["ram_critical"]) <= 100, "invalid ram thresholds")
    _require(
        0 <= float(thresholds["temp_slope_warn"]) < float(thresholds["temp_slope_critical"]),
        "invalid temperature slope thresholds",
    )

    total_weight = float(weights["temp_abs"]) + float(weights["temp_slope"]) + float(weights["cpu_sustained"]) + float(weights["ram_pressure"])
    _require(0.99 <= total_weight <= 1.01, "risk_weights must sum to 1.0")
    _require(isinstance(actions["switch_power_saver_on_warn"], bool), "actions.switch_power_saver_on_warn must be bool")
    _require(isinstance(actions["restore_power_plan_on_cool"], bool), "actions.restore_power_plan_on_cool must be bool")
    _require(isinstance(actions["lower_process_priority_on_warn"], bool), "actions.lower_process_priority_on_warn must be bool")
    _require(isinstance(actions["toast_on_critical"], bool), "actions.toast_on_critical must be bool")
    _require(isinstance(actions["suspend_workloads_on_critical"], bool), "actions.suspend_workloads_on_critical must be bool")

    allowlist["priority_lower"] = _normalize_process_list(allowlist["priority_lower"])
    allowlist["kill_candidates"] = _normalize_process_list(allowlist["kill_candidates"])

    _require(isinstance(agent["enabled"], bool), "agent.enabled must be bool")
    _require(isinstance(agent["use_llm"], bool), "agent.use_llm must be bool")
    _require(str(agent["ollama_url"]).startswith("http"), "agent.ollama_url must be http(s)")
    _require(str(agent["ollama_model"]).strip() != "", "agent.ollama_model cannot be empty")
    _require(isinstance(agent["rule_based_fallback"], bool), "agent.rule_based_fallback must be bool")

    _require(str(accountability["policy_version"]).strip() != "", "accountability.policy_version cannot be empty")
    _require(isinstance(accountability["record_noop_decisions"], bool), "accountability.record_noop_decisions must be bool")
    _require(isinstance(accountability["allow_destructive_actions"], bool), "accountability.allow_destructive_actions must be bool")
    _require(isinstance(accountability["block_unconfirmed_actions"], bool), "accountability.block_unconfirmed_actions must be bool")

    _require(isinstance(ats["enabled"], bool), "ats.enabled must be bool")
    _require(int(ats["evaluation_interval_seconds"]) >= 10, "ats.evaluation_interval_seconds must be >= 10")
    _require(int(ats["toast_cooldown_seconds"]) >= 0, "ats.toast_cooldown_seconds must be >= 0")
    _require(0 <= float(ats["maintenance_toast_threshold"]) <= 100, "ats.maintenance_toast_threshold must be 0-100")
    _require(str(ats["script_path"]).strip() != "", "ats.script_path cannot be empty")

    _require(isinstance(event_log["enabled"], bool), "event_log.enabled must be bool")
    _require(int(event_log["look_back_hours"]) >= 1, "event_log.look_back_hours must be >= 1")


def load_config(path: str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError("config.yaml must define a YAML object at top level")

    config = _deep_merge(copy.deepcopy(DEFAULT_CONFIG), loaded)
    validate_config(config)
    return config
