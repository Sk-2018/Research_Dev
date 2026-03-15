import unittest
from unittest.mock import patch

from app.collector import collect_snapshot
from app.collector.battery import BatterySnapshot
from app.collector.cpu import CPUSnapshot
from app.collector.disk import DiskSnapshot
from app.collector.gpu import GPUSnapshot
from app.collector.memory import MemorySnapshot
from app.collector.power import PowerSnapshot


class TestCollectorSnapshot(unittest.TestCase):
    @patch("app.collector.power.collect")
    @patch("app.collector.battery.collect")
    @patch("app.collector.gpu.collect")
    @patch("app.collector.disk.collect")
    @patch("app.collector.memory.collect")
    @patch("app.collector.cpu.collect")
    def test_collect_snapshot_returns_nested_schema(
        self,
        cpu_collect,
        memory_collect,
        disk_collect,
        gpu_collect,
        battery_collect,
        power_collect,
    ) -> None:
        cpu_collect.return_value = CPUSnapshot(total_pct=42.0, temp_celsius=70.0, top_processes=[{"name": "python.exe"}])
        memory_collect.return_value = MemorySnapshot(ram_pct=60.0)
        disk_collect.return_value = DiskSnapshot(read_mb_s=1.5, write_mb_s=2.5)
        gpu_collect.return_value = GPUSnapshot(utilization_pct=10.0, source="test")
        battery_collect.return_value = BatterySnapshot(charge_pct=95.0, plugged=True)
        power_collect.return_value = PowerSnapshot(plan_name="Balanced")

        snapshot = collect_snapshot(top_n_processes=3)

        cpu_collect.assert_called_once_with(top_n=3)
        self.assertIn("timestamp", snapshot)
        self.assertEqual(snapshot["cpu"]["total_pct"], 42.0)
        self.assertEqual(snapshot["memory"]["ram_pct"], 60.0)
        self.assertEqual(snapshot["disk"]["write_mb_s"], 2.5)
        self.assertEqual(snapshot["gpu"]["source"], "test")
        self.assertEqual(snapshot["battery"]["charge_pct"], 95.0)
        self.assertEqual(snapshot["power"]["plan_name"], "Balanced")


if __name__ == "__main__":
    unittest.main()
