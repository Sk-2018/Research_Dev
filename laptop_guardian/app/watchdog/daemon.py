import os
import subprocess
import threading
import time

import psutil

from app.agent.jarvis import ask_jarvis
from app.collector.sensors import get_system_metrics
from app.watchdog.risk import RiskEngine


def _canonical_proc_name(name):
    canonical = (name or "").strip().lower()
    if canonical.endswith(".exe"):
        canonical = canonical[:-4]
    return canonical


class SafeNotifier:
    def __init__(self, logger):
        self._logger = logger
        self._backend = None
        try:
            from win10toast import ToastNotifier

            self._backend = ToastNotifier()
        except Exception as exc:
            self._logger.warning("Toast notifications unavailable: %s", exc)

    def notify(self, title, message, duration=4):
        if self._backend is not None:
            try:
                self._backend.show_toast(title, message, duration=duration, threaded=True)
                return
            except Exception as exc:
                self._logger.warning("Toast notification failed: %s", exc)
        self._logger.info("%s: %s", title, message)


class WatchdogDaemon(threading.Thread):
    def __init__(self, config, db, logger):
        super().__init__(daemon=True)
        self.config = config
        self.db = db
        self.logger = logger
        self.notifier = SafeNotifier(logger)
        self.risk_engine = RiskEngine(config)
        self.power_throttled = False
        self._self_pid = os.getpid()
        self._allowlist_kill = {_canonical_proc_name(name) for name in self.config["actions"].get("allowlist_kill", [])}
        self._never_kill = {_canonical_proc_name(name) for name in self.config["actions"].get("never_kill", [])}
        self._no_window_flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._stop_event = threading.Event()
        self._last_action_at = {}

    def stop(self):
        self._stop_event.set()

    def _in_cooldown(self, action_key):
        cooldown = int(self.config["actions"].get("action_cooldown_sec", 0))
        if cooldown <= 0:
            return False
        last_time = self._last_action_at.get(action_key, 0.0)
        return (time.time() - last_time) < cooldown

    def _mark_action(self, action_key):
        self._last_action_at[action_key] = time.time()

    def _is_kill_allowed(self, target):
        target_name = _canonical_proc_name(target)
        if not target_name:
            return False
        if target_name in self._never_kill:
            return False
        if self._allowlist_kill and target_name not in self._allowlist_kill:
            return False
        return True

    def _kill_processes_by_name(self, target):
        target_name = _canonical_proc_name(target)
        max_kills = int(self.config["actions"].get("max_kill_per_cycle", 1))
        killed = []
        failures = []
        for proc in psutil.process_iter(["pid", "name"]):
            if len(killed) >= max_kills:
                break
            try:
                pid = int(proc.info["pid"])
                if pid == self._self_pid:
                    continue
                proc_name = _canonical_proc_name(proc.info.get("name"))
                if proc_name != target_name:
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
        return killed, failures

    def _switch_power_plan(self, plan_guid):
        result = subprocess.run(
            ["powercfg", "-setactive", plan_guid],
            creationflags=self._no_window_flag,
            check=False,
            capture_output=True,
            text=True,
        )
        stderr = (result.stderr or "").strip()
        return result.returncode == 0, stderr

    def _record_action(self, risk_score, decision, outcome, details):
        self.db.insert_action(
            risk_score=risk_score,
            action=decision.get("action", "NONE"),
            target=decision.get("target", ""),
            reason=decision.get("reason", ""),
            outcome=outcome,
            details=details,
        )

    def execute_action(self, risk_score, decision, reasons):
        action = str(decision.get("action", "NONE")).upper()
        target = str(decision.get("target", "")).strip()
        reason = str(decision.get("reason", "")).strip()

        if self.config["actions"]["dry_run"]:
            self.logger.info("DRY RUN decision=%s target=%s reason=%s", action, target, reason)
            return "dry_run", {"reasons": reasons}

        if action == "NONE":
            return "noop", {"reasons": reasons}

        action_key = f"{action}:{_canonical_proc_name(target) or 'system'}"
        if self._in_cooldown(action_key):
            return "cooldown_skip", {"action_key": action_key, "reasons": reasons}

        if action == "THROTTLE_POWER":
            if self.power_throttled:
                return "already_throttled", {"reasons": reasons}

            ok, err = self._switch_power_plan(self.config["actions"]["power_saver_guid"])
            if ok:
                self.power_throttled = True
                self._mark_action(action_key)
                msg = "Thermal critical. Switched to Power Saver mode."
                self.notifier.notify("Jarvis Guardian", msg, duration=5)
                self.logger.warning(msg)
                return "success", {"reasons": reasons}
            self.logger.error("Failed to set power saver plan: %s", err)
            return "failed", {"error": err, "reasons": reasons}

        if action == "KILL_PROCESS":
            if not self._is_kill_allowed(target):
                return "blocked_not_allowed", {"target": target, "reasons": reasons}

            killed_pids, failures = self._kill_processes_by_name(target)
            if killed_pids:
                self._mark_action(action_key)
                msg = f"Terminated {len(killed_pids)} process(es): {target}"
                self.notifier.notify("Jarvis Guardian", msg, duration=5)
                self.logger.warning("%s (pids=%s)", msg, killed_pids)
                return "success", {"killed_pids": killed_pids, "reasons": reasons}

            if failures:
                self.logger.error("Failed to kill %s: %s", target, failures)
                return "failed", {"errors": failures, "reasons": reasons}
            return "noop_no_process", {"target": target, "reasons": reasons}

        return "unsupported_action", {"action": action, "reasons": reasons}

    def _try_restore_power(self, risk_score):
        if not self.power_throttled:
            return
        restore_threshold = int(self.config["thresholds"]["risk_score_restore"])
        if risk_score > restore_threshold:
            return
        ok, err = self._switch_power_plan(self.config["actions"]["balanced_guid"])
        decision = {"action": "RESTORE_POWER", "target": "system", "reason": "Risk cooled down"}
        if ok:
            self.power_throttled = False
            self.notifier.notify("Jarvis Guardian", "System cooled. Restored Balanced mode.", duration=4)
            self.logger.info("Restored balanced power mode")
            self._record_action(risk_score, decision, "success", {"restore_threshold": restore_threshold})
        else:
            self.logger.error("Failed to restore balanced power plan: %s", err)
            self._record_action(risk_score, decision, "failed", {"error": err})

    def run(self):
        poll_interval = max(1, int(self.config["system"]["poll_interval_sec"]))
        critical_threshold = int(self.config["thresholds"]["risk_score_critical"])
        self.logger.info("Watchdog daemon started with poll_interval=%ss", poll_interval)
        while not self._stop_event.is_set():
            try:
                metrics = get_system_metrics()
                risk, reasons = self.risk_engine.evaluate(metrics)
                metrics["risk_score"] = risk
                metrics["risk_reasons"] = reasons

                self.db.insert_metric(
                    metrics["cpu_percent"],
                    metrics["ram_percent"],
                    metrics["temp_c"],
                    risk,
                    metrics["top_processes"],
                )

                if risk >= critical_threshold:
                    decision = ask_jarvis(metrics, self.config, logger=self.logger)
                    outcome, details = self.execute_action(risk, decision, reasons)
                    self._record_action(risk, decision, outcome, details)
                else:
                    self._try_restore_power(risk)
            except Exception as exc:
                self.logger.exception("Watchdog loop error: %s", exc)

            self._stop_event.wait(poll_interval)

        self.logger.info("Watchdog daemon stopped")
