from __future__ import annotations

import json
from typing import Any

import requests


ALLOWED_ACTIONS = {
    "NONE",
    "THROTTLE_POWER",
    "RESTORE_POWER",
    "LOWER_PRIORITY",
    "SUSPEND_WORKLOADS",
    "KILL_PROCESS",
}


def _with_meta(
    decision: dict[str, Any],
    *,
    source: str,
    llm_requested: bool,
    llm_used: bool,
    fallback_used: bool,
    llm_error: str = "",
) -> dict[str, Any]:
    enriched = dict(decision)
    enriched["meta"] = {
        "decision_source": source,
        "llm_requested": bool(llm_requested),
        "llm_used": bool(llm_used),
        "fallback_used": bool(fallback_used),
        "llm_error": str(llm_error or ""),
    }
    return enriched


def _canonical_name(name: str) -> str:
    value = (name or "").strip().lower()
    if value.endswith(".exe"):
        return value[:-4]
    return value


def _safe_json_loads(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def normalize_decision(raw_decision: Any) -> dict[str, Any]:
    loaded = _safe_json_loads(raw_decision)
    if not isinstance(loaded, dict):
        return {
            "action": "NONE",
            "target": "",
            "reason": "Decision format invalid",
            "safety": {"requires_confirmation": False},
        }

    action = str(loaded.get("action", "NONE")).strip().upper()
    if action not in ALLOWED_ACTIONS:
        action = "NONE"

    target = str(loaded.get("target", "")).strip()
    reason = str(loaded.get("reason", "No reason")).strip() or "No reason"
    safety = loaded.get("safety")
    if not isinstance(safety, dict):
        safety = {"requires_confirmation": False}
    else:
        safety = {"requires_confirmation": bool(safety.get("requires_confirmation", False))}

    return {
        "action": action,
        "target": target,
        "reason": reason,
        "safety": safety,
    }


def _pick_top_allowed_process(snapshot: dict[str, Any], allowlist: list[str]) -> str:
    allow = {_canonical_name(name) for name in allowlist}
    top_processes = snapshot.get("top_processes", [])
    if not isinstance(top_processes, list):
        return ""
    for proc in top_processes:
        if not isinstance(proc, dict):
            continue
        name = str(proc.get("name", "")).strip()
        if not name:
            continue
        if allow and _canonical_name(name) not in allow:
            continue
        return name
    return ""


def rule_based_decision(snapshot: dict[str, Any], assessment: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    actions = config["actions"]
    allowlist = config["process_allowlist"]
    risk_level = str(assessment.get("risk_level", "normal")).lower()
    flags = assessment.get("risk_flags", [])
    if not isinstance(flags, list):
        flags = []

    if risk_level == "critical":
        if actions.get("suspend_workloads_on_critical", False):
            candidate = _pick_top_allowed_process(snapshot, allowlist.get("kill_candidates", []))
            if candidate:
                return {
                    "action": "SUSPEND_WORKLOADS",
                    "target": candidate,
                    "reason": "Critical risk with allowed workload candidate",
                    "safety": {"requires_confirmation": False},
                }
        if actions.get("switch_power_saver_on_warn", True):
            return {
                "action": "THROTTLE_POWER",
                "target": "system",
                "reason": f"Critical risk flags: {','.join(flags) if flags else 'n/a'}",
                "safety": {"requires_confirmation": False},
            }

    if risk_level == "warn":
        if actions.get("lower_process_priority_on_warn", True):
            candidate = _pick_top_allowed_process(snapshot, allowlist.get("priority_lower", []))
            if candidate:
                return {
                    "action": "LOWER_PRIORITY",
                    "target": candidate,
                    "reason": "Warning risk with high CPU workload",
                    "safety": {"requires_confirmation": False},
                }
        if actions.get("switch_power_saver_on_warn", True):
            return {
                "action": "THROTTLE_POWER",
                "target": "system",
                "reason": "Warning risk threshold reached",
                "safety": {"requires_confirmation": False},
            }

    return {
        "action": "NONE",
        "target": "",
        "reason": "No action required",
        "safety": {"requires_confirmation": False},
    }


def ask_jarvis(snapshot: dict[str, Any], assessment: dict[str, Any], config: dict[str, Any], logger: Any = None) -> dict[str, Any]:
    agent_cfg = config["agent"]
    if not agent_cfg.get("enabled", False) or not agent_cfg.get("use_llm", False):
        return _with_meta(
            rule_based_decision(snapshot, assessment, config),
            source="rule_based_policy",
            llm_requested=False,
            llm_used=False,
            fallback_used=False,
        )

    prompt = (
        "You are a Windows system safety controller.\n"
        f"Snapshot: {json.dumps(snapshot)}\n"
        f"Assessment: {json.dumps(assessment)}\n"
        "Return ONLY JSON: "
        '{"action":"NONE|THROTTLE_POWER|RESTORE_POWER|LOWER_PRIORITY|SUSPEND_WORKLOADS|KILL_PROCESS","target":"","reason":"","safety":{"requires_confirmation":false}}'
    )

    try:
        response = requests.post(
            str(agent_cfg["ollama_url"]),
            json={
                "model": str(agent_cfg["ollama_model"]),
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()
        decision = normalize_decision(payload.get("response", payload))
        if decision["action"] == "NONE" and agent_cfg.get("rule_based_fallback", True):
            fallback = rule_based_decision(snapshot, assessment, config)
            fallback["reason"] = f"LLM returned no-op, fallback: {fallback['reason']}"
            return _with_meta(
                fallback,
                source="rule_based_fallback_noop",
                llm_requested=True,
                llm_used=False,
                fallback_used=True,
            )
        return _with_meta(
            decision,
            source="llm",
            llm_requested=True,
            llm_used=True,
            fallback_used=False,
        )
    except Exception as exc:
        if logger:
            logger.warning("Jarvis LLM request failed: %s", exc)
        if agent_cfg.get("rule_based_fallback", True):
            fallback = rule_based_decision(snapshot, assessment, config)
            fallback["reason"] = f"LLM fallback: {fallback['reason']}"
            return _with_meta(
                fallback,
                source="rule_based_fallback_error",
                llm_requested=True,
                llm_used=False,
                fallback_used=True,
                llm_error=str(exc),
            )
        return _with_meta(
            normalize_decision(None),
            source="llm_error_no_fallback",
            llm_requested=True,
            llm_used=False,
            fallback_used=False,
            llm_error=str(exc),
        )
