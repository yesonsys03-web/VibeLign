# === ANCHOR: TEST_DOC_SOURCES_START ===
"""tests/test_doc_sources.py — Phase 1: doc_sources 모듈 테스트."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibelign.core.doc_sources import (
    DOC_SOURCES_SCHEMA_VERSION,
    MAX_FILES_PER_SOURCE,
    DocSources,
    add,
    fingerprint,
    load,
    normalize_source,
    remove,
    save,
)
from vibelign.core.meta_paths import MetaPaths


class DocSourcesLoadTest(unittest.TestCase):
    """load() 함수 테스트."""

    # === ANCHOR: TEST_DOC_SOURCES_LOAD_START ===
    def test_load_missing_file_returns_empty(self):
        """Test 1: load() on missing file returns DocSources(sources=[])."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            result = load(meta)
            self.assertEqual(result.sources, [])

    def test_load_empty_json_returns_empty(self):
        """Test 2a: load() on empty JSON returns DocSources(sources=[])."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dir()
            meta.doc_sources_path.write_text("", encoding="utf-8")
            result = load(meta)
            self.assertEqual(result.sources, [])

    def test_load_malformed_json_returns_empty(self):
        """Test 2b: load() on malformed JSON returns DocSources(sources=[])."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dir()
            meta.doc_sources_path.write_text("{not valid json}", encoding="utf-8")
            result = load(meta)
            self.assertEqual(result.sources, [])
    # === ANCHOR: TEST_DOC_SOURCES_LOAD_END ===


class DocSourcesRoundTripTest(unittest.TestCase):
    """save/load round-trip 테스트."""

    # === ANCHOR: TEST_DOC_SOURCES_ROUNDTRIP_START ===
    def test_roundtrip_keeps_sorted_and_deduped(self):
        """Test 3: Round-trip save/load keeps sources normalized, sorted, and deduped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            # Create dirs to register
            (root / "b_dir").mkdir()
            (root / "a_dir").mkdir()

            initial = DocSources(sources=["b_dir", "a_dir", "b_dir"])
            save(meta, initial)

            loaded = load(meta)
            # Should be sorted and deduped
            self.assertEqual(loaded.sources, ["a_dir", "b_dir"])
    # === ANCHOR: TEST_DOC_SOURCES_ROUNDTRIP_END ===


class NormalizeSourceTest(unittest.TestCase):
    """normalize_source() 테스트."""

    # === ANCHOR: TEST_DOC_SOURCES_NORMALIZE_START ===
    def test_normalize_accepts_valid_relative_path(self):
        """Test 4: normalize_source accepts .omc/plans (after creating that dir in tmpdir)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".omc" / "plans").mkdir(parents=True)
            result = normalize_source(root, ".omc/plans")
            self.assertEqual(result, ".omc/plans")

    def test_normalize_accepts_windows_style_backslash(self):
        """Test 5: normalize_source accepts foo\\bar Windows-style input → foo/bar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foo" / "bar").mkdir(parents=True)
            result = normalize_source(root, "foo\\bar")
            self.assertEqual(result, "foo/bar")

    def test_normalize_rejects_absolute_path(self):
        """Test 6: normalize_source rejects absolute path outside root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self.assertRaises(ValueError):
                normalize_source(root, "/tmp/some_other_dir")

    def test_normalize_rejects_parent_escape(self):
        """Test 7: normalize_source rejects ../escape."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self.assertRaises(ValueError):
                normalize_source(root, "../escape")

    def test_normalize_rejects_nonexistent_dir(self):
        """Test 8: normalize_source rejects non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self.assertRaises(ValueError):
                normalize_source(root, "no_such_dir")

    def test_normalize_windows_backslash_omc_plans(self):
        """Test W1: normalize_source converts .omc\\plans (Windows backslash) → .omc/plans."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".omc" / "plans").mkdir(parents=True)
            result = normalize_source(root, ".omc\\plans")
            self.assertEqual(result, ".omc/plans")

    def test_normalize_windows_backslash_nested(self):
        """Test W2: normalize_source converts foo\\bar\\baz → foo/bar/baz."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "foo" / "bar" / "baz").mkdir(parents=True)
            result = normalize_source(root, "foo\\bar\\baz")
            self.assertEqual(result, "foo/bar/baz")

    def test_normalize_rejects_unc_prefix(self):
        """Test W3: normalize_source rejects UNC prefix (\\\\?\\C:\\... form)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self.assertRaises(ValueError):
                normalize_source(root, "\\\\?\\C:\\some\\path")
    # === ANCHOR: TEST_DOC_SOURCES_NORMALIZE_END ===


class AddRemoveTest(unittest.TestCase):
    """add() / remove() 테스트."""

    # === ANCHOR: TEST_DOC_SOURCES_ADD_REMOVE_START ===
    def test_add_rejects_duplicate(self):
        """Test 9: add() rejects duplicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            (root / "my_dir").mkdir()
            add(meta, "my_dir")
            with self.assertRaises(ValueError):
                add(meta, "my_dir")

    def test_remove_rejects_builtin_source(self):
        """Test 10: remove() rejects built-in source paths (e.g., docs/wiki)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            with self.assertRaises(ValueError):
                remove(meta, "docs/wiki")

    def test_remove_rejects_unregistered_source(self):
        """Test 11: remove() rejects non-registered source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            (root / "some_dir").mkdir()
            with self.assertRaises(ValueError):
                remove(meta, "some_dir")
    # === ANCHOR: TEST_DOC_SOURCES_ADD_REMOVE_END ===


class FingerprintTest(unittest.TestCase):
    """fingerprint() 테스트."""

    # === ANCHOR: TEST_DOC_SOURCES_FINGERPRINT_START ===
    def test_fingerprint_is_deterministic(self):
        """Test 12a: fingerprint() is deterministic (same input → same output)."""
        sources = [".omc/plans", ".sisyphus/plans"]
        fp1 = fingerprint(sources)
        fp2 = fingerprint(sources)
        self.assertEqual(fp1, fp2)
        self.assertTrue(fp1.startswith("sha256:"))

    def test_fingerprint_differs_when_sources_change(self):
        """Test 12b: fingerprint() differs when sources change."""
        fp_a = fingerprint([".omc/plans"])
        fp_b = fingerprint([".omc/plans", ".sisyphus/plans"])
        self.assertNotEqual(fp_a, fp_b)

    def test_fingerprint_order_independent(self):
        """Test 12c: fingerprint() is independent of input order."""
        fp1 = fingerprint(["b", "a"])
        fp2 = fingerprint(["a", "b"])
        self.assertEqual(fp1, fp2)

    def test_fingerprint_empty_list(self):
        """Test 12d: fingerprint() on empty list is deterministic."""
        fp1 = fingerprint([])
        fp2 = fingerprint([])
        self.assertEqual(fp1, fp2)
        self.assertTrue(fp1.startswith("sha256:"))
    # === ANCHOR: TEST_DOC_SOURCES_FINGERPRINT_END ===


class AtomicWriteTest(unittest.TestCase):
    """원자적 쓰기 테스트."""

    # === ANCHOR: TEST_DOC_SOURCES_ATOMIC_START ===
    def test_no_tmp_files_after_save(self):
        """Test 13: After save(), no .tmp files remain in .vibelign/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            sources = DocSources(sources=[])
            save(meta, sources)

            vibelign_dir = root / ".vibelign"
            tmp_files = list(vibelign_dir.glob("*.tmp"))
            self.assertEqual(tmp_files, [], f"Temp files found: {tmp_files}")

    def test_concurrent_load_save_no_partial_json(self):
        """Test 14: Concurrent load/save never exposes partial JSON (no JSONDecodeError)."""
        import threading
        import json as _json

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            meta = MetaPaths(root)
            # Seed initial valid state
            save(meta, DocSources(sources=[]))

            errors: list[Exception] = []
            iterations = 200
            stop_event = threading.Event()

            def writer():
                toggle = False
                for _ in range(iterations):
                    if stop_event.is_set():
                        break
                    sources = DocSources(sources=["a_dir"] if toggle else [])
                    try:
                        save(meta, sources)
                    except Exception as exc:  # noqa: BLE001
                        errors.append(exc)
                    toggle = not toggle

            def reader():
                for _ in range(iterations):
                    if stop_event.is_set():
                        break
                    try:
                        result = load(meta)
                        # Must be a valid DocSources with a list
                        if not isinstance(result.sources, list):
                            errors.append(
                                AssertionError(f"sources is not a list: {result.sources!r}")
                            )
                    except _json.JSONDecodeError as exc:
                        errors.append(exc)
                    except Exception:  # noqa: BLE001
                        pass  # OSError during read is acceptable, JSONDecodeError is not

            t_writer = threading.Thread(target=writer)
            t_reader = threading.Thread(target=reader)
            t_writer.start()
            t_reader.start()
            t_writer.join(timeout=10)
            t_reader.join(timeout=10)

            if errors:
                raise AssertionError(
                    f"Concurrent load/save produced {len(errors)} error(s): {errors[0]!r}"
                )
    # === ANCHOR: TEST_DOC_SOURCES_ATOMIC_END ===


# === ANCHOR: TEST_DOC_SOURCES_CONSTANTS_START ===
class ConstantsTest(unittest.TestCase):
    """모듈 상수 테스트."""

    def test_max_files_per_source(self):
        self.assertEqual(MAX_FILES_PER_SOURCE, 2000)

    def test_schema_version(self):
        self.assertEqual(DOC_SOURCES_SCHEMA_VERSION, 1)
# === ANCHOR: TEST_DOC_SOURCES_CONSTANTS_END ===


if __name__ == "__main__":
    unittest.main()
# === ANCHOR: TEST_DOC_SOURCES_END ===
