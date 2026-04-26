import unittest
from pathlib import Path

from vibelign.core.meta_paths import MetaPaths


class MetaPathsTest(unittest.TestCase):
    def test_vibelign_paths_and_report_names(self):
        root = Path("/tmp/example")
        meta = MetaPaths(root)
        self.assertEqual(meta.vibelign_dir, root / ".vibelign")
        self.assertEqual(meta.project_map_path, root / ".vibelign" / "project_map.json")
        self.assertEqual(
            meta.report_path("doctor", "md"),
            root / ".vibelign" / "reports" / "doctor_latest.md",
        )
        self.assertEqual(
            meta.report_path("patch", "json"),
            root / ".vibelign" / "reports" / "patch_latest.json",
        )
        self.assertEqual(meta.doc_sources_path, root / ".vibelign" / "doc_sources.json")
        self.assertEqual(meta.work_memory_path, root / ".vibelign" / "work_memory.json")


if __name__ == "__main__":
    unittest.main()
