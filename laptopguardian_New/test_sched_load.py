import unittest


class TestSchedulerLoad(unittest.TestCase):
    def test_scheduler_module_loads(self) -> None:
        from app.watchdog.scheduler import GuardianScheduler

        self.assertEqual(GuardianScheduler.__name__, "GuardianScheduler")


if __name__ == "__main__":
    unittest.main()
