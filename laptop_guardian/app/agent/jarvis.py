import json

import requests

ALLOWED_ACTIONS = {"KILL_PROCESS", "THROTTLE_POWER", "NONE"}


def _canonical_name(name):
    value = (name or "").strip().lower()
    if value.endswith(".exe"):
        value = value[:-4]
    return value


def _normalize_decision(raw_decision):
    if isinstance(raw_decision, str):
        try:
            raw_decision = json.loads(raw_decision)
        except json.JSONDecodeError:
            return {
                "action": "NONE",
                "target": "",
                "reason": "LLM returned invalid JSON",
                "safety": {"requires_confirmation": False},
            }

    if not isinstance(raw_decision, dict):
        return {
            "action": "NONE",
            "target": "",
            "reason": "LLM returned unexpected response format",
            "safety": {"requires_confirmation": False},
        }

    action = str(raw_decision.get("action", "NONE")).upper()
    if action not in ALLOWED_ACTIONS:
        action = "NONE"

    target = str(raw_decision.get("target", "")).strip()
    reason = str(raw_decision.get("reason", "No reason provided")).strip() or "No reason provided"
    safety = raw_decision.get("safety")
    if not isinstance(safety, dict):
        safety = {"requires_confirmation": False}
    else:
        safety = {"requires_confirmation": bool(safety.get("requires_confirmation", False))}

    return {"action": action, "target": target, "reason": reason, "safety": safety}


def _find_kill_candidate(metrics, config):
    allowlist = {_canonical_name(name) for name in config["actions"].get("allowlist_kill", [])}
    never_kill = {_canonical_name(name) for name in config["actions"].get("never_kill", [])}
    for proc in metrics.get("top_processes", []):
        name = str(proc.get("name", "")).strip()
        cpu = float(proc.get("cpu", 0.0) or 0.0)
        canon = _canonical_name(name)
        if not canon:
            continue
        if canon in never_kill:
            continue
        if allowlist and canon not in allowlist:
            continue
        if cpu >= 25:
            return name
    return ""


def _rule_decision(metrics, config):
    critical = int(config["thresholds"]["risk_score_critical"])
    risk = int(metrics.get("risk_score", 0))
    if risk < critical:
        return {"action": "NONE", "target": "", "reason": "Risk below critical threshold", "safety": {"requires_confirmation": False}}

    kill_candidate = _find_kill_candidate(metrics, config)
    if risk >= min(100, critical + 10) and kill_candidate:
        return {
            "action": "KILL_PROCESS",
            "target": kill_candidate,
            "reason": f"Sustained critical risk; top process candidate {kill_candidate}",
            "safety": {"requires_confirmation": False},
        }

    return {
        "action": "THROTTLE_POWER",
        "target": "system",
        "reason": "Critical risk score",
        "safety": {"requires_confirmation": False},
    }


def ask_jarvis(metrics, config, logger=None):
    if not config["agent"]["use_llm"]:
        return _rule_decision(metrics, config)

    allowlist = config["actions"].get("allowlist_kill", [])
    never_kill = config["actions"].get("never_kill", [])
    prompt = (
        "You are a Windows thermal watchdog controller.\n"
        f"Telemetry: {json.dumps(metrics)}\n"
        f"Allowed kill targets: {allowlist}\n"
        f"Protected processes (never kill): {never_kill}\n"
        "Choose the safest mitigation.\n"
        'Output ONLY valid JSON: {"action":"KILL_PROCESS|THROTTLE_POWER|NONE","target":"process_name.exe|system|","reason":"...","safety":{"requires_confirmation":false}}'
    )

    try:
        response = requests.post(
            config["agent"]["ollama_url"],
            json={
                "model": config["agent"]["model"],
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=int(config["agent"].get("timeout_sec", 5)),
        )
        response.raise_for_status()
        payload = response.json()
        decision = _normalize_decision(payload.get("response", "{}"))

        # Enforce a defensive fallback if LLM asks for an invalid action/target.
        if decision["action"] == "KILL_PROCESS" and not decision["target"]:
            decision = _rule_decision(metrics, config)
        return decision
    except Exception as exc:
        if logger:
            logger.warning("LLM request failed: %s", exc)
        fallback = _rule_decision(metrics, config)
        fallback["reason"] = f"LLM error fallback: {exc}"
        return fallback
