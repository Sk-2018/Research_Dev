import logging
import threading
import time
import unittest


class TestImports(unittest.TestCase):
    def test_core_imports_match_current_api(self) -> None:
        from app.collector import collect_all, collect_snapshot
        from app.risk.scorer import RiskResult, RiskScorer, TIER_CRITICAL, TIER_WARN, compute
        from app.storage import Database, GuardianDB
        from app.watchdog.actions import ActionExecutor, SafeNotifier

        self.assertEqual(time.__name__, "time")
        self.assertEqual(logging.__name__, "logging")
        self.assertEqual(threading.__name__, "threading")
        self.assertIs(collect_all, collect_snapshot)
        self.assertTrue(callable(compute))
        self.assertTrue(issubclass(RiskScorer, object))
        self.assertTrue(issubclass(RiskResult, object))
        self.assertEqual(TIER_WARN, "warn")
        self.assertEqual(TIER_CRITICAL, "critical")
        self.assertIs(Database, GuardianDB)
        self.assertTrue(issubclass(ActionExecutor, object))
        self.assertTrue(issubclass(SafeNotifier, object))


if __name__ == "__main__":
    unittest.main()
