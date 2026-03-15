import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from vibelign.commands.vib_init_cmd import _ensure_core_rule_files, run_vib_init


class VibInitFilesTest(unittest.TestCase):
    def test_init_creates_core_rule_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ensure_core_rule_files(root)
            self.assertTrue((root / "AI_DEV_SYSTEM_SINGLE_FILE.md").exists())
            self.assertTrue((root / "AGENTS.md").exists())

    def test_init_writes_project_map_prd_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = Path.cwd()
            try:
                os.chdir(root)
                (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
                (root / "services_auth.py").write_text(
                    "def login():\n    return True\n", encoding="utf-8"
                )
                (root / "ui_window.py").write_text(
                    "def render():\n    return 'ok'\n", encoding="utf-8"
                )
                (root / "engine_patch.py").write_text(
                    "def build_patch():\n    return {}\n", encoding="utf-8"
                )
                (root / "large_module.py").write_text(
                    "\n".join("print('x')" for _ in range(300)) + "\n",
                    encoding="utf-8",
                )

                run_vib_init(SimpleNamespace())
            finally:
                os.chdir(previous)

            payload = json.loads(
                (root / ".vibelign" / "project_map.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["schema_version"], 1)
            self.assertIn("main.py", payload["entry_files"])
            self.assertIn("ui_window.py", payload["ui_modules"])
            self.assertIn("engine_patch.py", payload["core_modules"])
            self.assertIn("services_auth.py", payload["service_modules"])
            self.assertNotIn("services_auth.py", payload["core_modules"])
            self.assertIn("large_module.py", payload["large_files"])
            self.assertEqual(payload["file_count"], 5)
            self.assertIn("generated_at", payload)
            self.assertTrue(str(payload["generated_at"]).endswith("Z"))


if __name__ == "__main__":
    unittest.main()
