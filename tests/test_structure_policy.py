import tempfile
import unittest
from pathlib import Path

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.structure_policy import (
    classify_structure_path,
    small_fix_line_threshold,
)


class StructurePolicyTest(unittest.TestCase):
    def test_small_fix_line_threshold_reads_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            _ = meta.config_path.write_text(
                "schema_version: 1\nsmall_fix_line_threshold: 7\n",
                encoding="utf-8",
            )

            self.assertEqual(small_fix_line_threshold(meta), 7)

    def test_classify_structure_path_keeps_core_as_production(self) -> None:
        self.assertEqual(classify_structure_path("vibelign/core/auth.py"), "production")
        self.assertEqual(classify_structure_path("tests/test_auth.py"), "tests")
        self.assertEqual(classify_structure_path("docs/MANUAL.md"), "docs")


if __name__ == "__main__":
    unittest.main()
