"""tests/test_doc_sources_cmd.py — Phase 5: vib_doc_sources_cmd 테스트."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ensure_stub_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    sys.modules[name] = package


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_ensure_stub_package("vibelign", ROOT / "vibelign")
_ensure_stub_package("vibelign.core", ROOT / "vibelign" / "core")
_ensure_stub_package("vibelign.commands", ROOT / "vibelign" / "commands")
_load_module("vibelign.core.meta_paths", ROOT / "vibelign" / "core" / "meta_paths.py")
_load_module("vibelign.core.doc_sources", ROOT / "vibelign" / "core" / "doc_sources.py")
_load_module("vibelign.core.docs_cache", ROOT / "vibelign" / "core" / "docs_cache.py")
_load_module("vibelign.core.docs_visualizer", ROOT / "vibelign" / "core" / "docs_visualizer.py")
_load_module("vibelign.core.docs_index_cache", ROOT / "vibelign" / "core" / "docs_index_cache.py")
docs_build_cmd = _load_module(
    "vibelign.commands.vib_docs_build_cmd",
    ROOT / "vibelign" / "commands" / "vib_docs_build_cmd.py",
)
doc_sources_cmd = _load_module(
    "vibelign.commands.vib_doc_sources_cmd",
    ROOT / "vibelign" / "commands" / "vib_doc_sources_cmd.py",
)


def _capture_stdout(fn) -> dict:
    """Run fn(), capture stdout, parse as JSON."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn()
    return json.loads(buf.getvalue().strip())


class DocSourcesCmdTest(unittest.TestCase):

    def _make_project(self) -> Path:
        tmp = tempfile.mkdtemp()
        root = Path(tmp)
        (root / ".vibelign").mkdir()
        (root / "PROJECT_CONTEXT.md").write_text("# Project\n\nHello.\n", encoding="utf-8")
        return root

    def _with_root(self, root: Path):
        """Patch VIBELIGN_PROJECT_ROOT env so _resolve_root() resolves to root."""
        import os
        old = os.environ.get("VIBELIGN_PROJECT_ROOT")
        os.environ["VIBELIGN_PROJECT_ROOT"] = str(root)
        return old

    def _restore_root(self, old):
        import os
        if old is None:
            os.environ.pop("VIBELIGN_PROJECT_ROOT", None)
        else:
            os.environ["VIBELIGN_PROJECT_ROOT"] = old

    def test_list_returns_ok_empty(self):
        """list on fresh project returns ok=True, sources=[], entries has built-in docs."""
        root = self._make_project()
        old = self._with_root(root)
        try:
            result = _capture_stdout(lambda: doc_sources_cmd.run_vib_doc_sources_list(Namespace()))
            self.assertTrue(result["ok"])
            self.assertEqual(result["sources"], [])
            self.assertIsInstance(result["entries"], list)
            self.assertIsInstance(result["warnings"], list)
        finally:
            self._restore_root(old)
            import shutil; shutil.rmtree(root, ignore_errors=True)

    def test_add_returns_ok_with_source(self):
        """add registers source, rebuild returns entries including the source."""
        root = self._make_project()
        extra_dir = root / "extra_docs"
        extra_dir.mkdir()
        (extra_dir / "test.md").write_text("# Extra\n\nContent.\n", encoding="utf-8")
        old = self._with_root(root)
        try:
            args = Namespace(path="extra_docs")
            result = _capture_stdout(lambda: doc_sources_cmd.run_vib_doc_sources_add(args))
            self.assertTrue(result["ok"])
            self.assertIn("extra_docs", result["sources"])
            paths = [e["path"] for e in result["entries"]]
            self.assertTrue(any("extra_docs" in p for p in paths))
        finally:
            self._restore_root(old)
            import shutil; shutil.rmtree(root, ignore_errors=True)

    def test_remove_returns_ok_source_gone(self):
        """add then remove: source disappears from sources list."""
        root = self._make_project()
        extra_dir = root / "extra_docs"
        extra_dir.mkdir()
        (extra_dir / "test.md").write_text("# Extra\n\nContent.\n", encoding="utf-8")
        old = self._with_root(root)
        try:
            # Add first
            add_args = Namespace(path="extra_docs")
            _capture_stdout(lambda: doc_sources_cmd.run_vib_doc_sources_add(add_args))

            # Remove
            rm_args = Namespace(path="extra_docs")
            result = _capture_stdout(lambda: doc_sources_cmd.run_vib_doc_sources_remove(rm_args))
            self.assertTrue(result["ok"])
            self.assertNotIn("extra_docs", result["sources"])
        finally:
            self._restore_root(old)
            import shutil; shutil.rmtree(root, ignore_errors=True)

    def test_add_missing_path_emits_error(self):
        """add with empty path emits ok=False JSON."""
        root = self._make_project()
        old = self._with_root(root)
        try:
            args = Namespace(path="")
            buf = io.StringIO()
            with redirect_stdout(buf):
                try:
                    doc_sources_cmd.run_vib_doc_sources_add(args)
                except SystemExit:
                    pass
            result = json.loads(buf.getvalue().strip())
            self.assertFalse(result["ok"])
            self.assertIn("error", result)
        finally:
            self._restore_root(old)
            import shutil; shutil.rmtree(root, ignore_errors=True)

    def test_remove_missing_path_emits_error(self):
        """remove with empty path emits ok=False JSON."""
        root = self._make_project()
        old = self._with_root(root)
        try:
            args = Namespace(path="")
            buf = io.StringIO()
            with redirect_stdout(buf):
                try:
                    doc_sources_cmd.run_vib_doc_sources_remove(args)
                except SystemExit:
                    pass
            result = json.loads(buf.getvalue().strip())
            self.assertFalse(result["ok"])
            self.assertIn("error", result)
        finally:
            self._restore_root(old)
            import shutil; shutil.rmtree(root, ignore_errors=True)

    def test_entries_have_source_root_for_custom(self):
        """Extra source entries in hidden dirs (allowlist-only paths) get Custom + source_root."""
        root = self._make_project()
        # Use a hidden dir that only gets indexed via extra-source allowlist, not by iter_markdown_files.
        extra_dir = root / ".custom_plans"
        extra_dir.mkdir()
        (extra_dir / "test.md").write_text("# Extra\n\nContent.\n", encoding="utf-8")
        old = self._with_root(root)
        try:
            args = Namespace(path=".custom_plans")
            result = _capture_stdout(lambda: doc_sources_cmd.run_vib_doc_sources_add(args))
            self.assertTrue(result["ok"])
            custom_entries = [e for e in result["entries"] if e.get("category") == "Custom"]
            self.assertTrue(len(custom_entries) > 0, "Expected at least one Custom entry from hidden dir")
            for entry in custom_entries:
                self.assertIsNotNone(entry.get("source_root"), "source_root should be set for Custom entries")
        finally:
            self._restore_root(old)
            import shutil; shutil.rmtree(root, ignore_errors=True)

    def test_remove_builtin_source_emits_error(self):
        """remove 시 built-in source(docs/wiki 등)는 CLI 레벨에서 ok=False를 반환한다."""
        root = self._make_project()
        old = self._with_root(root)
        try:
            args = Namespace(path="docs/wiki")
            buf = io.StringIO()
            with redirect_stdout(buf):
                try:
                    doc_sources_cmd.run_vib_doc_sources_remove(args)
                except SystemExit:
                    pass
            result = json.loads(buf.getvalue().strip())
            self.assertFalse(result["ok"], "Removing a built-in source should return ok=False")
            self.assertIn("error", result, "Response should include an 'error' field")
        finally:
            self._restore_root(old)
            import shutil; shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
