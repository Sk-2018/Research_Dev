from __future__ import annotations

import threading
import time
from typing import Any

from app.agent.jarvis import ask_jarvis
from app.collector import collect_snapshot
from app.risk.scorer import RiskScorer
from app.watchdog.ats_evaluator import ATSEvalResult, evaluate as evaluate_ats
from app.watchdog.actions import ActionExecutor


class GuardianScheduler(threading.Thread):
    def __init__(self, config: dict[str, Any], db: Any, logger: Any) -> None:
        super().__init__(daemon=True)
        self.config = config
        self.db = db
        self.logger = logger
        self.scorer = RiskScorer(config)
        self.executor = ActionExecutor(config, logger)
        self._stop_event = threading.Event()
        self._latest_ats_result = ATSEvalResult()
        self._last_ats_toast_at = 0.0
        self._last_ats_toast_verdict = "CLEAN"

    def stop(self) -> None:
        self._stop_event.set()

    def _agent_mode(self) -> str:
        agent_cfg = self.config.get("agent", {})
        enabled = bool(agent_cfg.get("enabled", False))
        use_llm = bool(agent_cfg.get("use_llm", False))
        if enabled and use_llm:
            return "llm"
        if enabled and not use_llm:
            return "rule_based"
        return "disabled_rule_based"

    def _policy_version(self) -> str:
        accountability = self.config.get("accountability", {})
        return str(accountability.get("policy_version", "unknown"))

    @staticmethod
    def _ats_severity(verdict: str) -> int:
        order = {
            "CLEAN": 0,
            "ADVISORY": 1,
            "MAINTENANCE_NEEDED": 2,
            "CRITICAL_MAINTENANCE": 3,
        }
        return order.get(str(verdict or "").upper(), 0)

    @staticmethod
    def _decision_meta(decision: dict[str, Any]) -> dict[str, Any]:
        meta = decision.get("meta", {})
        if not isinstance(meta, dict):
            return {}
        return meta

    def _enrich_action_details(
        self,
        *,
        decision: dict[str, Any],
        assessment: dict[str, Any],
        details: dict[str, Any] | None,
    ) -> dict[str, Any]:
        decision_meta = self._decision_meta(decision)
        enriched = dict(details or {})
        enriched["agent_mode"] = self._agent_mode()
        enriched["policy_version"] = self._policy_version()
        enriched["risk_flags"] = assessment.get("risk_flags", [])
        enriched["decision_source"] = str(decision_meta.get("decision_source", "unknown"))
        enriched["llm_requested"] = bool(decision_meta.get("llm_requested", False))
        enriched["llm_used"] = bool(decision_meta.get("llm_used", False))
        enriched["fallback_used"] = bool(decision_meta.get("fallback_used", False))
        enriched["llm_error"] = str(decision_meta.get("llm_error", ""))
        enriched["actor"] = "guardian_scheduler"
        enriched["decision"] = {
            "action": str(decision.get("action", "NONE")),
            "target": str(decision.get("target", "")),
            "reason": str(decision.get("reason", "")),
            "requires_confirmation": bool(
                decision.get("safety", {}).get("requires_confirmation", False)
                if isinstance(decision.get("safety"), dict)
                else False
            ),
        }
        return enriched

    def _record_ats_result(self, ats_result: ATSEvalResult) -> None:
        self.db.insert_ats_evaluation(ats_result)
        self._latest_ats_result = ats_result

    def _maybe_fire_ats_toast(self, ats_result: ATSEvalResult) -> None:
        ats_cfg = self.config.get("ats", {})
        threshold = float(ats_cfg.get("maintenance_toast_threshold", 40.0))
        cooldown = max(0, int(ats_cfg.get("toast_cooldown_seconds", 1800)))
        verdict = str(ats_result.verdict)
        score = float(ats_result.maintenance_score)
        if score < threshold or self._ats_severity(verdict) < self._ats_severity("MAINTENANCE_NEEDED"):
            self._last_ats_toast_verdict = verdict
            return

        now = time.time()
        crossed_up = self._ats_severity(verdict) > self._ats_severity(self._last_ats_toast_verdict)
        cooldown_elapsed = (now - self._last_ats_toast_at) >= cooldown
        if not crossed_up and not cooldown_elapsed:
            return

        reasons = "; ".join(ats_result.top_reasons[:3]) or "System cleanup recommended"
        title = "ATS Maintenance Required"
        if verdict == "CRITICAL_MAINTENANCE":
            title = "ATS Critical Maintenance Required"
        self.executor.notifier.notify(title, f"Score {score:.0f}/100 | {reasons}", duration=6)
        self.db.insert_action(
            risk_score=int(round(score)),
            risk_level=verdict.lower(),
            action="ATS_MAINTENANCE_ALERT",
            target="maintenance_script",
            reason=reasons,
            outcome="toast_fired",
            details={
                "policy_version": self._policy_version(),
                "agent_mode": "ats_evaluator",
                "decision_source": "ats_threshold_cross",
                "maintenance_score": score,
                "verdict": verdict,
                "top_reasons": ats_result.top_reasons[:5],
            },
        )
        self.logger.warning("ATS maintenance alert fired: verdict=%s score=%.1f", verdict, score)
        self._last_ats_toast_at = now
        self._last_ats_toast_verdict = verdict

    def run_cycle(self) -> tuple[dict[str, Any], dict[str, Any]]:
        top_n = int(self.config["general"].get("top_n_processes", 10))
        snapshot = collect_snapshot(top_n_processes=top_n)
        assessment = self.scorer.evaluate(snapshot)
        ats_result = ATSEvalResult()
        if self.config.get("ats", {}).get("enabled", True):
            ats_result = evaluate_ats(snapshot, self.config)
            if ats_result.fresh_scan or self.db.get_latest_ats_evaluation() is None:
                self._record_ats_result(ats_result)
            self._maybe_fire_ats_toast(ats_result)

        self.db.insert_metric(snapshot, assessment)
        self.logger.info(
            "sample cpu=%.1f ram=%.1f temp=%.1f risk=%s (%s)",
            float(snapshot.get("cpu_percent", 0.0)),
            float(snapshot.get("ram_percent", 0.0)),
            float(snapshot.get("temp_c", -1.0)),
            assessment.get("risk_score"),
            assessment.get("risk_level"),
        )

        level = str(assessment.get("risk_level", "normal"))
        accountability = self.config.get("accountability", {})
        record_noop = bool(accountability.get("record_noop_decisions", True))

        if level in {"warn", "critical"}:
            decision = ask_jarvis(snapshot, assessment, self.config, logger=self.logger)
            outcome, details = self.executor.execute(decision, assessment)
            enriched_details = self._enrich_action_details(decision=decision, assessment=assessment, details=details)
            self.db.insert_action(
                risk_score=int(assessment.get("risk_score", 0)),
                risk_level=level,
                action=str(decision.get("action", "NONE")),
                target=str(decision.get("target", "")),
                reason=str(decision.get("reason", "")),
                outcome=outcome,
                details=enriched_details,
            )
        else:
            noop_decision = {
                "action": "NONE",
                "target": "",
                "reason": "Risk is normal; no mitigation required",
                "safety": {"requires_confirmation": False},
                "meta": {
                    "decision_source": "policy_noop",
                    "llm_requested": False,
                    "llm_used": False,
                    "fallback_used": False,
                    "llm_error": "",
                },
            }
            noop_outcome, noop_details = self.executor.execute(noop_decision, assessment)

            restore_recorded = False
            if self.config["actions"].get("restore_power_plan_on_cool", True):
                outcome, details = self.executor.restore_power_if_needed()
                if outcome != "noop":
                    restore_decision = {
                        "action": "RESTORE_POWER",
                        "target": "system",
                        "reason": "Risk cooled down",
                        "safety": {"requires_confirmation": False},
                        "meta": {
                            "decision_source": "policy_restore",
                            "llm_requested": False,
                            "llm_used": False,
                            "fallback_used": False,
                            "llm_error": "",
                        },
                    }
                    enriched_details = self._enrich_action_details(
                        decision=restore_decision,
                        assessment=assessment,
                        details=details,
                    )
                    self.db.insert_action(
                        risk_score=int(assessment.get("risk_score", 0)),
                        risk_level=level,
                        action="RESTORE_POWER",
                        target="system",
                        reason="Risk cooled down",
                        outcome=outcome,
                        details=enriched_details,
                    )
                    restore_recorded = True

            if record_noop and not restore_recorded:
                enriched_noop_details = self._enrich_action_details(
                    decision=noop_decision,
                    assessment=assessment,
                    details=noop_details,
                )
                self.db.insert_action(
                    risk_score=int(assessment.get("risk_score", 0)),
                    risk_level=level,
                    action="NONE",
                    target="",
                    reason="Risk is normal; no mitigation required",
                    outcome=noop_outcome,
                    details=enriched_noop_details,
                )

        return snapshot, assessment

    def run(self) -> None:
        interval = max(1, int(float(self.config["general"].get("sample_interval_seconds", 3))))
        self.logger.info("Scheduler started with interval=%ss", interval)
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as exc:
                self.logger.exception("scheduler loop failure: %s", exc)
            self._stop_event.wait(interval)
        self.logger.info("Scheduler stopped")
