"""Edge-case tests: vib init with special project conditions."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch

from vibelign.commands.vib_init_cmd import run_vib_init


class InitEdgeCasesTest(unittest.TestCase):
    """vib_init_cmd edge cases.

    run_vib_init uses Path.cwd() internally, so we patch os.getcwd.
    """

    def _run_init_in(self, tmp_path):
        with mock_patch("os.getcwd", return_value=str(tmp_path)):
            with mock_patch.object(Path, "cwd", return_value=tmp_path):
                return run_vib_init(None)

    def test_init_on_empty_directory(self):
        """Init on a completely empty directory should not crash."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._run_init_in(tmp_path)
            vibelign_dir = tmp_path / ".vibelign"
            self.assertTrue(vibelign_dir.exists())
            self.assertTrue((vibelign_dir / "project_map.json").exists())
            self.assertTrue((vibelign_dir / "config.yaml").exists())

    def test_init_creates_valid_project_map_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._run_init_in(tmp_path)
            map_path = tmp_path / ".vibelign" / "project_map.json"
            data = json.loads(map_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)
            self.assertIsInstance(data["entry_files"], list)
            self.assertIsInstance(data["file_count"], int)

    def test_init_twice_does_not_crash(self):
        """Running init twice should be safe (idempotent)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._run_init_in(tmp_path)
            self._run_init_in(tmp_path)
            vibelign_dir = tmp_path / ".vibelign"
            self.assertTrue(vibelign_dir.exists())

    def test_init_with_existing_corrupt_state(self):
        """Init should handle corrupt state.json gracefully (overwrites it)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vibelign_dir = tmp_path / ".vibelign"
            vibelign_dir.mkdir()
            (vibelign_dir / "state.json").write_text("{bad json}", encoding="utf-8")
            self._run_init_in(tmp_path)
            self.assertTrue((vibelign_dir / "project_map.json").exists())

    def test_init_project_with_source_files(self):
        """Init should detect source files in the project."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "main.py").write_text("print('hello')\n")
            (tmp_path / "utils.py").write_text("def foo(): pass\n")
            self._run_init_in(tmp_path)
            map_path = tmp_path / ".vibelign" / "project_map.json"
            data = json.loads(map_path.read_text(encoding="utf-8"))
            self.assertGreater(data["file_count"], 0)
            self.assertIn("main.py", data["entry_files"])

    def test_init_preserves_existing_rule_files(self):
        """Init should not overwrite existing AI_DEV_SYSTEM_SINGLE_FILE.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rule_file = tmp_path / "AI_DEV_SYSTEM_SINGLE_FILE.md"
            rule_file.write_text("custom content\n")
            self._run_init_in(tmp_path)
            self.assertEqual(rule_file.read_text(), "custom content\n")

    def test_init_empty_project_has_zero_file_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._run_init_in(tmp_path)
            map_path = tmp_path / ".vibelign" / "project_map.json"
            data = json.loads(map_path.read_text(encoding="utf-8"))
            self.assertEqual(data["file_count"], 0)
            self.assertEqual(data["entry_files"], [])


if __name__ == "__main__":
    unittest.main()
