import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_scan_cmd import run_vib_scan


class VibScanCommandTest(unittest.TestCase):
    def test_vib_scan_uses_opt_in_rust_project_scan_for_anchor_validation(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            _ = (root / ".vibelign" / "project_map.json").write_text("{}\n", encoding="utf-8")
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

            os.chdir(root)
            try:
                with patch.dict("os.environ", {"VIBELIGN_PROJECT_SCAN_RUST": "1"}, clear=False), patch(
                    "vibelign.commands.vib_anchor_cmd.run_vib_anchor"
                ) as anchor_scan, patch(
                    "vibelign.core.project_scan.scan_project_with_rust",
                    return_value=(
                        {
                            "result": "project_scan",
                            "files": [
                                {"path": "src/app.py", "category": "other", "imports": []},
                            ],
                        },
                        None,
                    ),
                ) as rust_scan, patch(
                    "vibelign.commands.vib_scan_cmd._write_project_map",
                    return_value={"file_count": 1, "anchor_index": {}},
                ):
                    run_vib_scan(Namespace(auto=False))
            finally:
                os.chdir(previous)

        anchor_scan.assert_called_once()
        rust_scan.assert_called_once_with(root.resolve())

    def test_vib_scan_invalidates_doctor_analysis_cache_after_project_map_refresh(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir()
            _ = (meta_dir / "project_map.json").write_text("{}\n", encoding="utf-8")
            _ = (meta_dir / "analysis_cache.json").write_text(
                '{"schema_version": 2, "project_mtime_hash": "stale"}\n',
                encoding="utf-8",
            )
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

            os.chdir(root)
            try:
                with patch("vibelign.commands.vib_anchor_cmd.run_vib_anchor"), patch(
                    "vibelign.commands.vib_scan_cmd._write_project_map",
                    return_value={"file_count": 1, "anchor_index": {}},
                ):
                    run_vib_scan(Namespace(auto=False))
            finally:
                os.chdir(previous)

            self.assertFalse((meta_dir / "analysis_cache.json").exists())


if __name__ == "__main__":
    _ = unittest.main()
