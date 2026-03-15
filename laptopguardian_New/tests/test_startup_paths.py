import os
import unittest
from pathlib import Path

from app.main import PROJECT_ROOT, load_config
from app.storage import Database, GuardianDB


class TestStartupPaths(unittest.TestCase):
    def test_load_config_resolves_project_root_paths(self) -> None:
        original_cwd = Path.cwd()
        try:
            os.chdir(PROJECT_ROOT / "app")
            cfg = load_config()
        finally:
            os.chdir(original_cwd)

        self.assertEqual(cfg["dashboard"]["port"], 8050)
        self.assertEqual(Path(cfg["general"]["db_path"]), PROJECT_ROOT / "guardian.db")
        self.assertEqual(Path(cfg["general"]["log_path"]), PROJECT_ROOT / "logs" / "guardian.log")

    def test_storage_package_exports_legacy_guardiandb_alias(self) -> None:
        self.assertIs(GuardianDB, Database)


if __name__ == "__main__":
    unittest.main()
