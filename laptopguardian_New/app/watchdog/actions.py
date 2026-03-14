from __future__ import annotations

import html
import os
import subprocess
import sys
from typing import Any

import psutil

from app.collector.power import BALANCED_GUID, POWER_SAVER_GUID, get_active_plan_guid, set_active_plan


def _canonical_name(name: str) -> str:
    value = (name or "").strip().lower()
    if value.endswith(".exe"):
        return value[:-4]
    return value


class SafeNotifier:
    def __init__(self, enabled: bool, logger: Any) -> None:
        self._enabled = bool(enabled)
        self._logger = logger
        self._backend = None
        if not self._enabled:
            return
        try:
            if sys.version_info < (3, 13):
                from win10toast import ToastNotifier  # type: ignore

                self._backend = ToastNotifier()
        except Exception as exc:
            self._logger.info("Toast notifier unavailable: %s", exc)

    def _powershell_toast(self, title: str, message: str) -> bool:
        escaped_title = html.escape(title, quote=True).replace("'", "&apos;")
        escaped_message = html.escape(message, quote=True).replace("'", "&apos;")
        xml = (
            "<toast><visual><binding template=\"ToastGeneric\">"
            f"<text>{escaped_title}</text><text>{escaped_message}</text>"
            "</binding></visual></toast>"
        )
        command = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null; "
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] > $null; "
            "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument; "
            f"$xml.LoadXml('{xml}'); "
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
            "$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('LaptopHealthGuardian'); "
            "$notifier.Show($toast)"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return result.returncode == 0
        except Exception as exc:
            self._logger.info("PowerShell toast failed: %s", exc)
            return False

    def notify(self, title: str, message: str, duration: int = 4) -> None:
        if self._backend is not None:
            try:
                self._backend.show_toast(title, message, duration=duration, threaded=True)
                return
            except Exception as exc:
                self._logger.warning("Toast notification failed: %s", exc)
        if self._powershell_toast(title, message):
            return
        self._logger.info("%s: %s", title, message)


class ActionExecutor:
    def __init__(self, config: dict[str, Any], logger: Any) -> None:
        self.config = config
        self.logger = logger
        self.dry_run = bool(config["general"].get("dry_run", False))
        self.accountability = config.get("accountability", {})
        self.policy_version = str(self.accountability.get("policy_version", "unknown"))
        self.allow_destructive_actions = bool(self.accountability.get("allow_destructive_actions", False))
        self.block_unconfirmed_actions = bool(self.accountability.get("block_unconfirmed_actions", True))
        self.priority_allowlist = {_canonical_name(name) for name in config["process_allowlist"].get("priority_lower", [])}
        self.kill_allowlist = {_canonical_name(name) for name in config["process_allowlist"].get("kill_candidates", [])}
        self._self_pid = os.getpid()
        self._power_saver_active = False
        self._previous_plan_guid = get_active_plan_guid()
        self.notifier = SafeNotifier(config["actions"].get("toast_on_critical", True), logger)

    def _base_details(self, decision: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        action = str(decision.get("action", "NONE")).upper()
        target = str(decision.get("target", "")).strip()
        safety = decision.get("safety", {})
        requires_confirmation = bool(safety.get("requires_confirmation", False)) if isinstance(safety, dict) else False
        return {
            "policy_version": self.policy_version,
            "requested_action": action,
            "requested_target": target,
            "requires_confirmation": requires_confirmation,
            "risk_level": str(assessment.get("risk_level", "unknown")),
            "risk_score": int(assessment.get("risk_score", 0) or 0),
            "dry_run": self.dry_run,
            "safety_checks": [],
        }

    @staticmethod
    def _merge_details(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        merged.update(extra or {})
        return merged

    def _set_power_saver(self) -> tuple[str, dict[str, Any]]:
        if self._power_saver_active:
            return "already_throttled", {}
        if self.dry_run:
            return "dry_run", {"plan": "power_saver"}
        ok, err = set_active_plan(POWER_SAVER_GUID)
        if ok:
            self._power_saver_active = True
            self.logger.warning("Switched system power plan to Power Saver")
            return "success", {"plan": POWER_SAVER_GUID}
        return "failed", {"error": err}

    def restore_power_if_needed(self) -> tuple[str, dict[str, Any]]:
        if not self._power_saver_active:
            return "noop", {}
        if self.dry_run:
            return "dry_run", {"plan": "balanced"}
        plan_to_restore = self._previous_plan_guid or BALANCED_GUID
        ok, err = set_active_plan(plan_to_restore)
        if ok:
            self._power_saver_active = False
            self.logger.info("Restored system power plan to %s", plan_to_restore)
            return "success", {"plan": plan_to_restore}
        return "failed", {"error": err}

    def _lower_priority(self, target_name: str) -> tuple[str, dict[str, Any]]:
        target = _canonical_name(target_name)
        if not target or target not in self.priority_allowlist:
            return "blocked_not_allowlisted", {"target": target_name}
        if self.dry_run:
            return "dry_run", {"target": target_name}

        lowered: list[int] = []
        failures: list[str] = []
        nice_value = getattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS", None)
        if nice_value is None:
            return "unsupported", {"reason": "priority lowering is only supported on Windows"}

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if int(proc.info["pid"]) == self._self_pid:
                    continue
                name = _canonical_name(str(proc.info.get("name", "")))
                if name != target:
                    continue
                proc.nice(nice_value)
                lowered.append(int(proc.info["pid"]))
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except (psutil.AccessDenied, psutil.Error) as exc:
                failures.append(str(exc))

        if lowered:
            return "success", {"pids": lowered}
        if failures:
            return "failed", {"errors": failures}
        return "noop_no_process", {"target": target_name}

    def _terminate_process(self, target_name: str) -> tuple[str, dict[str, Any]]:
        target = _canonical_name(target_name)
        if not target or target not in self.kill_allowlist:
            return "blocked_not_allowlisted", {"target": target_name}
        if self.dry_run:
            return "dry_run", {"target": target_name}

        killed: list[int] = []
        failures: list[str] = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = int(proc.info["pid"])
                if pid == self._self_pid:
                    continue
                name = _canonical_name(str(proc.info.get("name", "")))
                if name != target:
                    continue
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except psutil.TimeoutExpired:
                    proc.kill()
                killed.append(pid)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except (psutil.AccessDenied, psutil.Error) as exc:
                failures.append(str(exc))

        if killed:
            return "success", {"pids": killed}
        if failures:
            return "failed", {"errors": failures}
        return "noop_no_process", {"target": target_name}

    def execute(
        self,
        decision: dict[str, Any],
        assessment: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        action = str(decision.get("action", "NONE")).upper()
        target = str(decision.get("target", "")).strip()
        details = self._base_details(decision, assessment)
        safety_checks = details["safety_checks"]
        requires_confirmation = bool(details["requires_confirmation"])

        if action == "NONE":
            safety_checks.append("no_action_requested")
            return "noop", details

        if requires_confirmation and self.block_unconfirmed_actions:
            safety_checks.append("blocked_requires_confirmation")
            return "blocked_requires_confirmation", details

        if action == "THROTTLE_POWER":
            if not self.config["actions"].get("switch_power_saver_on_warn", True):
                safety_checks.append("blocked_switch_power_saver_on_warn_disabled")
                return "blocked_disabled", details
            safety_checks.append("switch_power_saver_on_warn_enabled")
            outcome, exec_details = self._set_power_saver()
            if outcome == "success" and assessment.get("risk_level") == "critical":
                self.notifier.notify("Laptop Guardian", "Critical risk detected: Power Saver enabled.", duration=5)
            return outcome, self._merge_details(details, exec_details)

        if action == "RESTORE_POWER":
            safety_checks.append("restore_requested")
            outcome, exec_details = self.restore_power_if_needed()
            return outcome, self._merge_details(details, exec_details)

        if action == "LOWER_PRIORITY":
            if not self.config["actions"].get("lower_process_priority_on_warn", True):
                safety_checks.append("blocked_lower_process_priority_on_warn_disabled")
                return "blocked_disabled", details
            safety_checks.append("lower_process_priority_on_warn_enabled")
            outcome, exec_details = self._lower_priority(target)
            return outcome, self._merge_details(details, exec_details)

        if action in {"SUSPEND_WORKLOADS", "KILL_PROCESS"}:
            if not self.config["actions"].get("suspend_workloads_on_critical", False):
                safety_checks.append("blocked_suspend_workloads_on_critical_disabled")
                return "blocked_disabled", details
            if not self.allow_destructive_actions:
                safety_checks.append("blocked_allow_destructive_actions_false")
                return "blocked_policy", details
            safety_checks.append("destructive_actions_allowed")
            outcome, exec_details = self._terminate_process(target)
            return outcome, self._merge_details(details, exec_details)

        safety_checks.append("unsupported_action_requested")
        return "unsupported_action", details
