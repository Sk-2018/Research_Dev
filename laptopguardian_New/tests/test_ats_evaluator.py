import copy
import unittest
from unittest.mock import patch

from app.configuration import DEFAULT_CONFIG
from app.watchdog.ats_evaluator import ATSSignal, evaluate


class TestATSEvaluator(unittest.TestCase):
    def setUp(self) -> None:
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.telemetry = {"temp_c": 55.0}

    @patch("app.watchdog.ats_evaluator.check_network_packet_loss")
    @patch("app.watchdog.ats_evaluator.check_dns_latency")
    @patch("app.watchdog.ats_evaluator.check_windows_update_cache")
    @patch("app.watchdog.ats_evaluator.check_docker_vhdx")
    @patch("app.watchdog.ats_evaluator.check_browser_cache")
    @patch("app.watchdog.ats_evaluator.check_temp_size")
    @patch("app.watchdog.ats_evaluator.check_disk_free")
    def test_evaluate_returns_maintenance_needed_for_high_signal_scores(
        self,
        disk_check,
        temp_check,
        browser_check,
        docker_check,
        wu_check,
        dns_check,
        ping_check,
    ) -> None:
        disk_check.return_value = ATSSignal("Disk", 10.0, "GB", "CRITICAL", "Disk low", 30.0)
        temp_check.return_value = ATSSignal("Temp", 1800.0, "MB", "CRITICAL", "Temp large", 15.0)
        browser_check.return_value = ATSSignal("Cache", 2500.0, "MB", "CRITICAL", "Cache large", 15.0)
        docker_check.return_value = ATSSignal("Docker", 25.0, "GB", "CRITICAL", "Docker large", 20.0)
        wu_check.return_value = ATSSignal("WU", 2100.0, "MB", "CRITICAL", "WU large", 10.0)
        dns_check.return_value = ATSSignal("DNS", 250.0, "ms", "CRITICAL", "DNS slow", 5.0)
        ping_check.return_value = ATSSignal("Ping", 25.0, "%", "CRITICAL", "Loss", 5.0)

        result = evaluate(self.telemetry, self.config, force=True)
        self.assertEqual(result.verdict, "CRITICAL_MAINTENANCE")
        self.assertGreaterEqual(result.maintenance_score, 90.0)
        self.assertTrue(result.fresh_scan)

    @patch("app.watchdog.ats_evaluator._heavy_signals")
    def test_evaluate_reuses_cached_heavy_scan_within_interval(self, heavy_signals) -> None:
        heavy_signals.return_value = [ATSSignal("Disk", 12.0, "GB", "CRITICAL", "Disk low", 30.0)]

        first = evaluate(self.telemetry, self.config, force=True)
        second = evaluate(self.telemetry, self.config, force=False)

        self.assertTrue(first.fresh_scan)
        self.assertFalse(second.fresh_scan)
        self.assertEqual(heavy_signals.call_count, 1)


if __name__ == "__main__":
    unittest.main()
