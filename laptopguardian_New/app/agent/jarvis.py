"""
Jarvis Agent: rule-based + optional LLM (Ollama) action proposer.
All actions are proposals only; execution requires executor validation.
"""
import json, logging, requests
from dataclasses import dataclass, field
from typing import Optional
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

ACTION_SCHEMA = {
    "type": "object",
    "required": ["action", "target", "reason", "confidence", "safety"],
    "properties": {
        "action":      {"type": "string", "enum": ["lower_priority", "switch_power_saver", "propose_terminate", "no_action", "notify"]},
        "target":      {"type": "string"},
        "reason":      {"type": "string"},
        "confidence":  {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "safety": {
            "type": "object",
            "required": ["requires_confirmation"],
            "properties": {
                "requires_confirmation": {"type": "boolean"},
                "is_destructive":        {"type": "boolean"},
            }
        }
    }
}


def validate_action(proposal: dict) -> bool:
    try:
        validate(instance=proposal, schema=ACTION_SCHEMA)
        return True
    except ValidationError as e:
        logger.error(f"Action schema validation failed: {e.message}")
        return False


def _rule_based_propose(telemetry: dict, cfg: dict) -> dict:
    """Deterministic rule-based fallback when no LLM is available."""
    cpu_pct   = telemetry.get("cpu", {}).get("total_pct", 0)
    temp_c    = telemetry.get("cpu", {}).get("temp_celsius") or 0
    thresholds = cfg.get("thresholds", {})
    procs = telemetry.get("cpu", {}).get("top_processes", [])
    top_proc = procs[0]["name"] if procs else "unknown"

    if temp_c >= thresholds.get("temp_critical", 88):
        return {
            "action": "propose_terminate",
            "target": top_proc,
            "reason": f"Temperature critical at {temp_c:.1f}°C; top CPU consumer is {top_proc}.",
            "confidence": 0.85,
            "safety": {"requires_confirmation": True, "is_destructive": True}
        }
    elif cpu_pct >= thresholds.get("cpu_warn", 80):
        return {
            "action": "lower_priority",
            "target": top_proc,
            "reason": f"CPU at {cpu_pct:.1f}%; lowering priority of {top_proc} to reduce heat.",
            "confidence": 0.90,
            "safety": {"requires_confirmation": False, "is_destructive": False}
        }
    elif temp_c >= thresholds.get("temp_warn", 75):
        return {
            "action": "switch_power_saver",
            "target": "system",
            "reason": f"Temperature elevated at {temp_c:.1f}°C; switching to power saver.",
            "confidence": 0.92,
            "safety": {"requires_confirmation": False, "is_destructive": False}
        }
    return {
        "action": "no_action",
        "target": "system",
        "reason": "System nominal.",
        "confidence": 0.99,
        "safety": {"requires_confirmation": False, "is_destructive": False}
    }


def _llm_propose(telemetry: dict, cfg: dict) -> Optional[dict]:
    agent_cfg  = cfg.get("agent", {})
    url        = agent_cfg.get("ollama_url", "http://localhost:11434/api/generate")
    model      = agent_cfg.get("ollama_model", "mistral")
    cpu_pct    = telemetry.get("cpu", {}).get("total_pct", 0)
    temp_c     = telemetry.get("cpu", {}).get("temp_celsius")
    ram_pct    = telemetry.get("memory", {}).get("ram_pct", 0)

    prompt = f"""You are a laptop thermal management agent for an AMD Ryzen 7 5700U laptop.
Current metrics: CPU={cpu_pct:.1f}%, Temp={temp_c}°C, RAM={ram_pct:.1f}%.
Top processes: {telemetry.get('cpu', {}).get('top_processes', [])[:3]}

Respond ONLY with valid JSON matching this schema exactly (no extra text):
{{"action": "<lower_priority|switch_power_saver|propose_terminate|no_action|notify>",
  "target": "<process_name_or_system>",
  "reason": "<concise explanation>",
  "confidence": <0.0-1.0>,
  "safety": {{"requires_confirmation": <true|false>, "is_destructive": <true|false>}}}}"""

    try:
        r = requests.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=15)
        r.raise_for_status()
        text = r.json().get("response", "")
        # Extract JSON from response
        start = text.find("{")
        end   = text.rfind("}") + 1
        proposal = json.loads(text[start:end])
        if validate_action(proposal):
            return proposal
    except Exception as e:
        logger.warning(f"LLM query failed: {e}; falling back to rules.")
    return None


def propose(telemetry: dict, cfg: dict) -> dict:
    agent_cfg = cfg.get("agent", {})
    if not agent_cfg.get("enabled", False):
        return _rule_based_propose(telemetry, cfg)
    if agent_cfg.get("use_llm", False):
        proposal = _llm_propose(telemetry, cfg)
        if proposal:
            return proposal
    return _rule_based_propose(telemetry, cfg)
