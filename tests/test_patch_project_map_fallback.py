import json
import tempfile
import unittest
from pathlib import Path

from vibelign.core.patch_suggester import suggest_patch


class PatchProjectMapFallbackTest(unittest.TestCase):
    def test_patch_suggester_falls_back_without_project_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "services_auth.py").write_text(
                "def login_guard():\n    return True\n", encoding="utf-8"
            )

            suggestion = suggest_patch(root, "add login guard")

            self.assertEqual(suggestion.target_file, "services_auth.py")

    def test_patch_suggester_falls_back_with_invalid_project_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "services_auth.py").write_text(
                "def login_guard():\n    return True\n", encoding="utf-8"
            )
            meta_dir = root / ".vibelign"
            meta_dir.mkdir()
            (meta_dir / "project_map.json").write_text(
                json.dumps({"schema_version": 999, "project_name": root.name}) + "\n",
                encoding="utf-8",
            )

            suggestion = suggest_patch(root, "add login guard")

            self.assertEqual(suggestion.target_file, "services_auth.py")


if __name__ == "__main__":
    unittest.main()
