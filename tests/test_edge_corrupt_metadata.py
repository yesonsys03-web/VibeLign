"""Edge-case tests: corrupt/invalid metadata files."""

import json
import tempfile
import unittest
from pathlib import Path

from vibelign.core.project_map import load_project_map, SUPPORTED_PROJECT_MAP_SCHEMA
from vibelign.core.doctor_v2 import analyze_project_v2, build_doctor_envelope
from vibelign.core.patch_suggester import load_anchor_metadata


class CorruptProjectMapTest(unittest.TestCase):
    """project_map.py with corrupt/edge-case data."""

    def _write_map(self, tmp, data):
        vibelign_dir = Path(tmp) / ".vibelign"
        vibelign_dir.mkdir(exist_ok=True)
        (vibelign_dir / "project_map.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def test_missing_project_map_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap, err = load_project_map(Path(tmp))
        self.assertIsNone(snap)
        self.assertIsNone(err)

    def test_invalid_json_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            vibelign_dir = Path(tmp) / ".vibelign"
            vibelign_dir.mkdir()
            (vibelign_dir / "project_map.json").write_text("{bad json", encoding="utf-8")
            snap, err = load_project_map(Path(tmp))
        self.assertIsNone(snap)
        self.assertEqual(err, "invalid_project_map")

    def test_wrong_schema_version_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_map(tmp, {"schema_version": 999})
            snap, err = load_project_map(Path(tmp))
        self.assertIsNone(snap)
        self.assertEqual(err, "unsupported_project_map_schema")

    def test_schema_version_as_string_returns_error(self):
        """schema_version="1" (string) != 1 (int) should be rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write_map(tmp, {"schema_version": "1"})
            snap, err = load_project_map(Path(tmp))
        self.assertIsNone(snap)
        self.assertEqual(err, "unsupported_project_map_schema")

    def test_entry_files_as_non_list_returns_empty_frozenset(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_map(
                tmp,
                {
                    "schema_version": SUPPORTED_PROJECT_MAP_SCHEMA,
                    "entry_files": "not_a_list",
                },
            )
            snap, err = load_project_map(Path(tmp))
        self.assertIsNotNone(snap)
        self.assertEqual(snap.entry_files, frozenset())

    def test_entry_files_with_non_string_items_filtered(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_map(
                tmp,
                {
                    "schema_version": SUPPORTED_PROJECT_MAP_SCHEMA,
                    "entry_files": ["main.py", 123, None, True],
                },
            )
            snap, err = load_project_map(Path(tmp))
        self.assertIsNotNone(snap)
        self.assertEqual(snap.entry_files, frozenset({"main.py"}))

    def test_file_count_as_string_defaults_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_map(
                tmp,
                {
                    "schema_version": SUPPORTED_PROJECT_MAP_SCHEMA,
                    "file_count": "not_int",
                },
            )
            snap, err = load_project_map(Path(tmp))
        self.assertIsNotNone(snap)
        self.assertEqual(snap.file_count, 0)

    def test_generated_at_as_int_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_map(
                tmp,
                {
                    "schema_version": SUPPORTED_PROJECT_MAP_SCHEMA,
                    "generated_at": 12345,
                },
            )
            snap, err = load_project_map(Path(tmp))
        self.assertIsNotNone(snap)
        self.assertIsNone(snap.generated_at)

    def test_empty_json_object_returns_schema_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_map(tmp, {})
            snap, err = load_project_map(Path(tmp))
        self.assertIsNone(snap)
        self.assertEqual(err, "unsupported_project_map_schema")


class CorruptAnchorIndexTest(unittest.TestCase):
    """patch_suggester.load_anchor_metadata with corrupt data."""

    def test_missing_anchor_index_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = load_anchor_metadata(Path(tmp))
        self.assertEqual(result, {})

    def test_invalid_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            vibelign_dir = Path(tmp) / ".vibelign"
            vibelign_dir.mkdir()
            (vibelign_dir / "anchor_index.json").write_text("{bad}", encoding="utf-8")
            result = load_anchor_metadata(Path(tmp))
        self.assertEqual(result, {})

    def test_files_key_not_dict_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            vibelign_dir = Path(tmp) / ".vibelign"
            vibelign_dir.mkdir()
            (vibelign_dir / "anchor_index.json").write_text(
                json.dumps({"files": "not_a_dict"}), encoding="utf-8"
            )
            result = load_anchor_metadata(Path(tmp))
        self.assertEqual(result, {})


class DoctorWithCorruptMapTest(unittest.TestCase):
    """doctor_v2 handles corrupt project_map gracefully."""

    def test_doctor_with_invalid_project_map_reports_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            vibelign_dir = Path(tmp) / ".vibelign"
            vibelign_dir.mkdir()
            (vibelign_dir / "project_map.json").write_text("{broken", encoding="utf-8")
            report = analyze_project_v2(Path(tmp))
        self.assertFalse(report.stats.get("project_map_loaded", True))
        issue_texts = [item["found"] for item in report.issues]
        self.assertTrue(
            any("읽을 수 없습니다" in t for t in issue_texts)
        )

    def test_doctor_envelope_with_corrupt_map_still_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            vibelign_dir = Path(tmp) / ".vibelign"
            vibelign_dir.mkdir()
            (vibelign_dir / "project_map.json").write_text("{broken", encoding="utf-8")
            envelope = build_doctor_envelope(Path(tmp))
        self.assertTrue(envelope["ok"])
        self.assertIsNone(envelope["error"])


if __name__ == "__main__":
    unittest.main()
