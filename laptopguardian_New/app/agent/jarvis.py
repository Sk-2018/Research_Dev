"""
Jarvis Agent: rule-based + optional LLM (Ollama) action proposer.
All actions are proposals only; execution requires executor validation.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Optional

import requests

try:
    from jsonschema import ValidationError, validate
except ImportError:  # pragma: no cover - exercised via fallback path
    ValidationError = ValueError
    validate = None


logger = logging.getLogger(__name__)

ACTION_SCHEMA = {
    "type": "object",
    "required": ["action", "target", "reason", "confidence", "safety"],
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "lower_priority",
                "switch_power_saver",
                "propose_terminate",
                "run_maintenance_script",
                "no_action",
                "notify",
            ],
        },
        "target": {"type": "string"},
        "reason": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "safety": {
            "type": "object",
            "required": ["requires_confirmation"],
            "properties": {
                "requires_confirmation": {"type": "boolean"},
                "is_destructive": {"type": "boolean"},
            },
        },
    },
}


def validate_action(proposal: dict) -> bool:
    if validate is None:
        return _validate_action_fallback(proposal)
    try:
        validate(instance=proposal, schema=ACTION_SCHEMA)
        return True
    except ValidationError as exc:
        logger.error("Action schema validation failed: %s", exc.message)
        return False


def _validate_action_fallback(proposal: dict) -> bool:
    allowed_actions = {
        "lower_priority",
        "switch_power_saver",
        "propose_terminate",
        "run_maintenance_script",
        "no_action",
        "notify",
    }
    if not isinstance(proposal, dict):
        logger.error("Action schema validation failed: proposal must be an object.")
        return False

    required = {"action", "target", "reason", "confidence", "safety"}
    if not required.issubset(proposal):
        logger.error("Action schema validation failed: missing required keys.")
        return False

    if proposal["action"] not in allowed_actions:
        logger.error("Action schema validation failed: invalid action '%s'.", proposal["action"])
        return False

    if not isinstance(proposal["target"], str) or not isinstance(proposal["reason"], str):
        logger.error("Action schema validation failed: target and reason must be strings.")
        return False

    confidence = proposal["confidence"]
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        logger.error("Action schema validation failed: confidence must be 0.0-1.0.")
        return False

    safety = proposal["safety"]
    if not isinstance(safety, dict) or "requires_confirmation" not in safety:
        logger.error("Action schema validation failed: missing safety.requires_confirmation.")
        return False

    if not isinstance(safety["requires_confirmation"], bool):
        logger.error("Action schema validation failed: requires_confirmation must be bool.")
        return False

    if "is_destructive" in safety and not isinstance(safety["is_destructive"], bool):
        logger.error("Action schema validation failed: is_destructive must be bool.")
        return False

    return True


def _rule_based_propose(telemetry: dict, cfg: dict) -> dict:
    cpu_pct = telemetry.get("cpu", {}).get("total_pct", 0)
    temp_c = telemetry.get("cpu", {}).get("temp_celsius") or 0
    thresholds = cfg.get("thresholds", {})
    processes = telemetry.get("cpu", {}).get("top_processes", [])
    top_process = processes[0]["name"] if processes else "unknown"

    if temp_c >= thresholds.get("temp_critical", 88):
        return {
            "action": "propose_terminate",
            "target": top_process,
            "reason": f"Temperature critical at {temp_c:.1f} C; top CPU consumer is {top_process}.",
            "confidence": 0.85,
            "safety": {"requires_confirmation": True, "is_destructive": True},
        }
    if cpu_pct >= thresholds.get("cpu_warn", 80):
        return {
            "action": "lower_priority",
            "target": top_process,
            "reason": f"CPU at {cpu_pct:.1f}%; lowering priority of {top_process} to reduce heat.",
            "confidence": 0.90,
            "safety": {"requires_confirmation": False, "is_destructive": False},
        }
    if temp_c >= thresholds.get("temp_warn", 75):
        return {
            "action": "switch_power_saver",
            "target": "system",
            "reason": f"Temperature elevated at {temp_c:.1f} C; switching to power saver.",
            "confidence": 0.92,
            "safety": {"requires_confirmation": False, "is_destructive": False},
        }
    return {
        "action": "no_action",
        "target": "system",
        "reason": "System nominal.",
        "confidence": 0.99,
        "safety": {"requires_confirmation": False, "is_destructive": False},
    }


def _ats_value(ats_result: object | None, key: str, default=None):
    if ats_result is None:
        return default
    if isinstance(ats_result, Mapping):
        return ats_result.get(key, default)
    return getattr(ats_result, key, default)


def _maintenance_propose(cfg: dict, ats_result: object | None) -> Optional[dict]:
    ats_cfg = cfg.get("ats", {})
    if not ats_cfg.get("enabled", False):
        return None

    maintenance_score = float(_ats_value(ats_result, "maintenance_score", 0.0) or 0.0)
    threshold = float(ats_cfg.get("maintenance_toast_threshold", 40.0))
    if maintenance_score < threshold:
        return None

    verdict = str(_ats_value(ats_result, "verdict", "MAINTENANCE_NEEDED"))
    top_reasons = _ats_value(ats_result, "top_reasons", []) or []
    reason_suffix = top_reasons[0] if top_reasons else "System maintenance indicators are elevated."
    confidence = min(0.95, 0.65 + maintenance_score / 200.0)

    return {
        "action": "run_maintenance_script",
        "target": str(ats_cfg.get("script_path", "ats_maintenance_script")),
        "reason": f"ATS score {maintenance_score:.1f}/100 ({verdict}). {reason_suffix}",
        "confidence": round(confidence, 2),
        "safety": {"requires_confirmation": True, "is_destructive": False},
    }


def _llm_propose(telemetry: dict, cfg: dict, ats_result: object | None = None) -> Optional[dict]:
    agent_cfg = cfg.get("agent", {})
    url = agent_cfg.get("ollama_url", "http://localhost:11434/api/generate")
    model = agent_cfg.get("ollama_model", "mistral")
    cpu_pct = telemetry.get("cpu", {}).get("total_pct", 0)
    temp_c = telemetry.get("cpu", {}).get("temp_celsius")
    ram_pct = telemetry.get("memory", {}).get("ram_pct", 0)
    ats_score = float(_ats_value(ats_result, "maintenance_score", 0.0) or 0.0)
    ats_verdict = _ats_value(ats_result, "verdict", "CLEAN")
    ats_reasons = _ats_value(ats_result, "top_reasons", []) or []

    prompt = f"""You are a laptop thermal management agent for an AMD Ryzen 7 5700U laptop.
Current metrics: CPU={cpu_pct:.1f}%, Temp={temp_c} C, RAM={ram_pct:.1f}%.
Top processes: {telemetry.get('cpu', {}).get('top_processes', [])[:3]}
ATS maintenance score={ats_score:.1f}/100, verdict={ats_verdict}, reasons={ats_reasons[:2]}.

Respond ONLY with valid JSON matching this schema exactly (no extra text):
{{"action": "<lower_priority|switch_power_saver|propose_terminate|run_maintenance_script|no_action|notify>",
  "target": "<process_name_or_system>",
  "reason": "<concise explanation>",
  "confidence": <0.0-1.0>,
  "safety": {{"requires_confirmation": <true|false>, "is_destructive": <true|false>}}}}"""

    try:
        response = requests.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=15)
        response.raise_for_status()
        text = response.json().get("response", "")
        start = text.find("{")
        end = text.rfind("}") + 1
        proposal = json.loads(text[start:end])
        if validate_action(proposal):
            return proposal
    except Exception as exc:
        logger.warning("LLM query failed: %s; falling back to rules.", exc)
    return None


def propose(telemetry: dict, cfg: dict, ats_result: object | None = None) -> dict:
    thermal_proposal = _rule_based_propose(telemetry, cfg)
    if thermal_proposal["action"] != "no_action":
        return thermal_proposal

    maintenance_proposal = _maintenance_propose(cfg, ats_result)
    if maintenance_proposal:
        return maintenance_proposal

    agent_cfg = cfg.get("agent", {})
    if not agent_cfg.get("enabled", False):
        return thermal_proposal
    if agent_cfg.get("use_llm", False):
        proposal = _llm_propose(telemetry, cfg, ats_result=ats_result)
        if proposal:
            return proposal
    return thermal_proposal
