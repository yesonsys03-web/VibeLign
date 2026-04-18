import json
import tempfile
import unittest
from pathlib import Path

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.structure_policy import (
    classify_structure_path,
    load_active_plan_payload,
    small_fix_line_threshold,
)
from vibelign.mcp.mcp_state_store import save_planning_session


class StructurePolicyTest(unittest.TestCase):
    def test_classify_structure_path_marks_patch_module_as_production(self) -> None:
        self.assertEqual(
            classify_structure_path("vibelign/patch/patch_output.py"),
            "production",
        )

    def test_classify_structure_path_separates_non_vibelign_python_files(self) -> None:
        self.assertEqual(
            classify_structure_path("scripts/release.py"),
            "non_vibelign_production",
        )

    def test_load_active_plan_payload_treats_unicode_errors_as_broken_plan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            save_planning_session(
                meta,
                {
                    "active": True,
                    "plan_id": "bad",
                    "feature": "bad",
                    "override": False,
                    "override_reason": None,
                    "created_at": "2026-04-10T00:00:00Z",
                    "updated_at": "2026-04-10T00:00:00Z",
                },
            )
            (meta.plans_dir / "bad.json").write_bytes(b"\xff\xfe\x00\x00")

            payload, plan_id, error = load_active_plan_payload(meta)

            self.assertIsNone(payload)
            self.assertEqual(plan_id, "bad")
            self.assertEqual(error, "broken_plan")

    def test_small_fix_line_threshold_falls_back_when_config_is_not_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            meta.config_path.write_bytes(b"\xff\xfe\x00\x00")

            self.assertEqual(small_fix_line_threshold(meta), 30)


if __name__ == "__main__":
    unittest.main()
