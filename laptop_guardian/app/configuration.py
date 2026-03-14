import copy
from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "system": {
        "poll_interval_sec": 5,
        "db_path": "guardian_metrics.db",
        "log_path": "guardian.log",
        "history_points": 120,
    },
    "thresholds": {
        "temp_warn": 80.0,
        "temp_critical": 90.0,
        "cpu_sustained_warn": 85.0,
        "risk_score_critical": 80,
        "risk_score_restore": 30,
    },
    "actions": {
        "dry_run": False,
        "allowlist_kill": ["node.exe", "python.exe", "chrome.exe"],
        "never_kill": ["explorer.exe", "svchost.exe", "system", "dash", "Code.exe"],
        "power_saver_guid": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "balanced_guid": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "action_cooldown_sec": 30,
        "max_kill_per_cycle": 1,
    },
    "agent": {
        "use_llm": False,
        "ollama_url": "http://localhost:11434/api/generate",
        "model": "phi3",
        "timeout_sec": 5,
    },
    "dashboard": {
        "host": "127.0.0.1",
        "port": 8050,
        "refresh_ms": 5000,
    },
}


def _deep_merge(base, override):
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _normalize_name_list(values):
    if not isinstance(values, list):
        raise ValueError("Process lists must be arrays in config.yaml")
    cleaned = []
    for item in values:
        name = str(item).strip()
        if not name:
            continue
        cleaned.append(name)
    return cleaned


def _validate_config(config):
    system = config["system"]
    thresholds = config["thresholds"]
    actions = config["actions"]
    agent = config["agent"]
    dashboard = config["dashboard"]

    _require(float(system["poll_interval_sec"]) >= 1, "system.poll_interval_sec must be >= 1")
    _require(int(system["history_points"]) >= 30, "system.history_points must be >= 30")
    _require(float(thresholds["temp_warn"]) > 0, "thresholds.temp_warn must be > 0")
    _require(
        float(thresholds["temp_critical"]) > float(thresholds["temp_warn"]),
        "thresholds.temp_critical must be > thresholds.temp_warn",
    )
    _require(
        0 <= int(thresholds["risk_score_restore"]) < int(thresholds["risk_score_critical"]) <= 100,
        "risk_score_restore must be < risk_score_critical and both within 0-100",
    )
    _require(0 <= float(thresholds["cpu_sustained_warn"]) <= 100, "thresholds.cpu_sustained_warn must be 0-100")
    _require(int(actions["action_cooldown_sec"]) >= 0, "actions.action_cooldown_sec must be >= 0")
    _require(int(actions["max_kill_per_cycle"]) >= 1, "actions.max_kill_per_cycle must be >= 1")
    _require(int(agent["timeout_sec"]) >= 1, "agent.timeout_sec must be >= 1")
    _require(1 <= int(dashboard["port"]) <= 65535, "dashboard.port must be 1-65535")

    actions["allowlist_kill"] = _normalize_name_list(actions["allowlist_kill"])
    actions["never_kill"] = _normalize_name_list(actions["never_kill"])

    # Make sure critical process list always protects this app and shell.
    protected = {"python.exe", "powershell.exe", "cmd.exe"}
    existing = {name.lower() for name in actions["never_kill"]}
    for proc in sorted(protected):
        if proc not in existing:
            actions["never_kill"].append(proc)


def load_config(config_path):
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    config = _deep_merge(copy.deepcopy(DEFAULT_CONFIG), loaded)
    _validate_config(config)
    return config
