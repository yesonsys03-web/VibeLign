import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from argparse import Namespace
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
_load_module(
    "vibelign.core.docs_visualizer", ROOT / "vibelign" / "core" / "docs_visualizer.py"
)
_load_module(
    "vibelign.core.docs_index_cache",
    ROOT / "vibelign" / "core" / "docs_index_cache.py",
)
docs_build_cmd = _load_module(
    "vibelign.commands.vib_docs_build_cmd",
    ROOT / "vibelign" / "commands" / "vib_docs_build_cmd.py",
)


class DocsBuildCmdTest(unittest.TestCase):
    def test_build_single_file_writes_visual_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            target = root / "PROJECT_CONTEXT.md"
            target.write_text(
                "# Session Handoff\n\nHello docs build.\n", encoding="utf-8"
            )

            result = docs_build_cmd.build_docs_visual_cache(root, "PROJECT_CONTEXT.md")

            artifact_path = (
                root / ".vibelign" / "docs_visual" / "PROJECT_CONTEXT.md.json"
            )
            self.assertEqual(result["count"], 1)
            self.assertTrue(artifact_path.exists())
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["title"], "Session Handoff")
            self.assertEqual(payload["source_path"], str(target.resolve()))

    def test_full_build_writes_multiple_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "docs" / "wiki").mkdir(parents=True)
            (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
            (root / "PROJECT_CONTEXT.md").write_text(
                "# Context\n\nAlpha\n", encoding="utf-8"
            )
            (root / "docs" / "wiki" / "index.md").write_text(
                "# Wiki\n\nBeta\n", encoding="utf-8"
            )
            (root / "docs" / "superpowers" / "plans" / "plan.md").write_text(
                "# Plan\n\nGamma\n", encoding="utf-8"
            )

            result = docs_build_cmd.build_docs_visual_cache(root)

            self.assertEqual(result["count"], 3)
            self.assertTrue(
                (
                    root / ".vibelign" / "docs_visual" / "PROJECT_CONTEXT.md.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / ".vibelign"
                    / "docs_visual"
                    / "docs"
                    / "wiki"
                    / "index.md.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / ".vibelign"
                    / "docs_visual"
                    / "docs"
                    / "superpowers"
                    / "plans"
                    / "plan.md.json"
                ).exists()
            )

    def test_docs_index_includes_plain_text_csv_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "notes.txt").write_text("plain notes\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "table.csv").write_text("name,value\na,1\n", encoding="utf-8")
            (root / "docs" / "data.json").write_text('{"ok": true}\n', encoding="utf-8")

            entries = docs_build_cmd.build_docs_index(root)
            paths = {entry.path for entry in entries}

            self.assertIn("notes.txt", paths)
            self.assertIn("docs/table.csv", paths)
            self.assertIn("docs/data.json", paths)

    def test_bad_input_does_not_leave_partial_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "docs" / "wiki").mkdir(parents=True)
            (root / "PROJECT_CONTEXT.md").write_text(
                "# Context\n\nAlpha\n", encoding="utf-8"
            )
            (root / "docs" / "wiki" / "bad.md").write_bytes(b"\xff\xfe\x00\x00")

            with self.assertRaises(ValueError):
                docs_build_cmd.build_docs_visual_cache(root)

            docs_visual_dir = root / ".vibelign" / "docs_visual"
            self.assertFalse(docs_visual_dir.exists())

    def test_run_command_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "PROJECT_CONTEXT.md").write_text(
                "# Context\n\nAlpha\n", encoding="utf-8"
            )
            old_cwd = Path.cwd()
            old_env = os.environ.get("VIBELIGN_PROJECT_ROOT")
            try:
                os.environ["VIBELIGN_PROJECT_ROOT"] = str(root)
                os.chdir(root)
                from io import StringIO
                import contextlib

                buf = StringIO()
                with contextlib.redirect_stdout(buf):
                    docs_build_cmd.run_vib_docs_build(Namespace(path=None, json=True))
                payload = json.loads(buf.getvalue())
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["count"], 1)
            finally:
                os.chdir(old_cwd)
                if old_env is None:
                    os.environ.pop("VIBELIGN_PROJECT_ROOT", None)
                else:
                    os.environ["VIBELIGN_PROJECT_ROOT"] = old_env

    def test_docs_build_generates_heuristic_diagram_when_no_authored_mermaid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            target = root / "README.md"
            target.write_text(
                "# Demo\n\n## Install\n\n1. Copy files\n2. Add API key\n3. Restart app\n",
                encoding="utf-8",
            )

            docs_build_cmd.build_docs_visual_cache(root, "README.md")

            payload = json.loads(
                (root / ".vibelign" / "docs_visual" / "README.md.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(payload["diagram_blocks"]), 1)
            self.assertEqual(payload["diagram_blocks"][0]["provenance"], "heuristic")
            self.assertEqual(payload["diagram_blocks"][0]["generator"], "step-flow-v1")

    def test_docs_build_preserves_authored_mermaid_over_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            target = root / "README.md"
            target.write_text(
                "# Demo\n\n## Diagram\n\n```mermaid\nflowchart TD\n  A[Start] --> B[Done]\n```\n\n## Install\n\n1. Copy\n2. Configure\n3. Restart\n",
                encoding="utf-8",
            )

            docs_build_cmd.build_docs_visual_cache(root, "README.md")

            payload = json.loads(
                (root / ".vibelign" / "docs_visual" / "README.md.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(payload["diagram_blocks"]), 1)
            self.assertEqual(payload["diagram_blocks"][0]["provenance"], "authored")
            self.assertEqual(
                payload["diagram_blocks"][0]["generator"], "authored-mermaid-v1"
            )
            self.assertIn("flowchart TD", payload["diagram_blocks"][0]["source"])

    def test_docs_build_huge_doc_keeps_authored_and_skips_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            authored = root / "huge-authored.md"
            plain = root / "huge-plain.md"
            filler = "\n".join(f"line {index}" for index in range(1300))
            authored.write_text(
                f"# Huge\n\n```mermaid\nflowchart TD\n  A[Start] --> B[Done]\n```\n\n{filler}\n",
                encoding="utf-8",
            )
            plain.write_text(
                f"# Huge\n\n## Intro\n\nAlpha\n\n## Usage\n\nBeta\n\n{filler}\n",
                encoding="utf-8",
            )

            docs_build_cmd.build_docs_visual_cache(root, "huge-authored.md")
            docs_build_cmd.build_docs_visual_cache(root, "huge-plain.md")

            authored_payload = json.loads(
                (
                    root / ".vibelign" / "docs_visual" / "huge-authored.md.json"
                ).read_text(encoding="utf-8")
            )
            plain_payload = json.loads(
                (root / ".vibelign" / "docs_visual" / "huge-plain.md.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(authored_payload["diagram_blocks"]), 1)
            self.assertEqual(
                authored_payload["diagram_blocks"][0]["provenance"], "authored"
            )
            self.assertEqual(plain_payload["diagram_blocks"], [])
            self.assertTrue(
                any(
                    "auto_diagram_skipped_huge_doc" in warning
                    for warning in plain_payload.get("warnings", [])
                )
            )


class ExtraSourceIndexTest(unittest.TestCase):
    """Phase 2: extra source 통합 인덱싱 테스트."""

    def _get_docs_cache(self):
        import sys
        return sys.modules["vibelign.core.docs_cache"]

    def _get_doc_sources(self):
        import sys
        return sys.modules["vibelign.core.doc_sources"]

    def _get_meta_paths(self):
        import sys
        return sys.modules["vibelign.core.meta_paths"]

    def test_extra_source_shows_in_index(self):
        """등록된 .omc/plans/plan.md 가 index에 category=Custom, source_root='.omc/plans'로 나타난다."""
        docs_cache = self._get_docs_cache()
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# My Plan\n\nContent here.\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            entries = docs_cache.build_docs_index(root)
            custom_entries = [e for e in entries if e.source_root == ".omc/plans"]

            self.assertEqual(len(custom_entries), 1)
            self.assertEqual(custom_entries[0].category, "Custom")
            self.assertEqual(custom_entries[0].source_root, ".omc/plans")
            self.assertIn(".omc/plans/plan.md", custom_entries[0].path)

    def test_extra_source_indexes_plain_text_csv_and_json(self):
        docs_cache = self._get_docs_cache()
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "note.txt").write_text("note\n", encoding="utf-8")
            (root / ".omc" / "plans" / "table.csv").write_text("a,b\n", encoding="utf-8")
            (root / ".omc" / "plans" / "data.json").write_text("{}\n", encoding="utf-8")

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            entries = docs_cache.build_docs_index(root)
            paths = {e.path for e in entries if e.source_root == ".omc/plans"}

            self.assertEqual(
                paths,
                {".omc/plans/note.txt", ".omc/plans/table.csv", ".omc/plans/data.json"},
            )

    def test_unregistered_hidden_is_excluded(self):
        """.omc/other/x.md 는 등록 안 했으면 index에 나타나지 않는다."""
        docs_cache = self._get_docs_cache()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "other").mkdir(parents=True)
            (root / ".omc" / "other" / "x.md").write_text(
                "# Secret\n", encoding="utf-8"
            )

            entries = docs_cache.build_docs_index(root)
            paths = [e.path for e in entries]
            self.assertFalse(
                any(".omc" in p for p in paths),
                f"Unregistered hidden path should not appear; got: {paths}",
            )

    def test_registered_root_hidden_subdir_is_pruned(self):
        """.omc/plans/.archive/x.md 는 등록된 source 아래여도 prune된다."""
        docs_cache = self._get_docs_cache()
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "visible.md").write_text(
                "# Visible\n", encoding="utf-8"
            )
            (root / ".omc" / "plans" / ".archive").mkdir()
            (root / ".omc" / "plans" / ".archive" / "hidden.md").write_text(
                "# Hidden\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            entries = docs_cache.build_docs_index(root)
            paths = [e.path for e in entries]
            self.assertTrue(
                any(".omc/plans/visible.md" in p for p in paths),
                "Visible file in registered source should appear",
            )
            self.assertFalse(
                any(".archive" in p for p in paths),
                f"Hidden subdir should be pruned even under registered source; got: {paths}",
            )

    def test_builtin_wins_over_extra(self):
        """docs/superpowers/plans/foo.md 가 built-in Plan이고, 같은 dir이 extra source로도 등록되면 한 번만, category=Plan으로 나타난다."""
        docs_cache = self._get_docs_cache()
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
            (root / "docs" / "superpowers" / "plans" / "foo.md").write_text(
                "# Foo Plan\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, "docs/superpowers/plans")

            entries = docs_cache.build_docs_index(root)
            matching = [e for e in entries if "foo.md" in e.path]

            self.assertEqual(len(matching), 1, "Should appear exactly once")
            self.assertEqual(matching[0].category, "Plan", "Built-in category wins")

    def test_max_files_per_source_warning(self):
        """MAX_FILES_PER_SOURCE를 2로 patch하고 3개 파일 생성 시, 2개 entry + warning."""
        docs_cache = self._get_docs_cache()
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            for i in range(3):
                (root / ".omc" / "plans" / f"doc{i}.md").write_text(
                    f"# Doc {i}\n", encoding="utf-8"
                )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            # Monkey-patch MAX_FILES_PER_SOURCE=2 on the doc_sources reference that
            # docs_cache actually uses (_DOC_SOURCES), which may differ from the
            # module object returned by sys.modules when test isolation is in play.
            _doc_sources_ref = docs_cache._DOC_SOURCES
            original = _doc_sources_ref.MAX_FILES_PER_SOURCE
            try:
                _doc_sources_ref.MAX_FILES_PER_SOURCE = 2
                entries, warnings = docs_cache.build_docs_index_with_warnings(root)
            finally:
                _doc_sources_ref.MAX_FILES_PER_SOURCE = original

            custom_entries = [e for e in entries if e.source_root == ".omc/plans"]
            self.assertEqual(len(custom_entries), 2, "Only 2 entries due to cap")
            self.assertTrue(
                any(".omc/plans" in w for w in warnings),
                f"Warning should mention the capped source; got: {warnings}",
            )
            self.assertTrue(
                any("2" in w for w in warnings),
                f"Warning should mention the cap count; got: {warnings}",
            )


class Phase3CacheParityTest(unittest.TestCase):
    """Phase 3: docs_index cache allowlist/fingerprint parity 테스트."""

    def _get_doc_sources(self):
        return sys.modules["vibelign.core.doc_sources"]

    def _get_docs_index_cache(self):
        return sys.modules["vibelign.core.docs_index_cache"]

    def _get_meta_paths(self):
        return sys.modules["vibelign.core.meta_paths"]

    def test_docs_index_cache_includes_allowlist_and_fingerprint(self):
        """rebuild 후 docs_index.json 에 현재 schema_version, allowlist, sources_fingerprint 가 포함된다."""
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# My Plan\n\nContent here.\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            docs_build_cmd.rebuild_docs_index_cache(root)

            cache_path = root / ".vibelign" / "docs_index.json"
            self.assertTrue(cache_path.exists())
            payload = json.loads(cache_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["schema_version"], 3)
            self.assertIn("allowlist", payload)
            self.assertEqual(
                payload["allowlist"]["extra_source_roots"], [".omc/plans"]
            )
            self.assertIn("sources_fingerprint", payload)
            expected_fp = doc_sources.fingerprint([".omc/plans"])
            self.assertEqual(payload["sources_fingerprint"], expected_fp)

    def test_cache_miss_on_fingerprint_change(self):
        """캐시 기록 후 doc_sources 변경 시 read_docs_index_cache 가 None 을 반환한다."""
        doc_sources = self._get_doc_sources()
        docs_index_cache = self._get_docs_index_cache()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# Plan\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            # Build and write cache
            docs_build_cmd.rebuild_docs_index_cache(root)

            # Mutate doc_sources (add a new source that doesn't exist yet — use docs/ which is always valid)
            (root / "extra_dir").mkdir()
            doc_sources.add(meta, "extra_dir")

            # Cache should now be a miss
            result = docs_index_cache.read_docs_index_cache(meta)
            self.assertIsNone(result, "Cache should miss after doc_sources fingerprint change")

    def test_cache_hit_on_matching_fingerprint(self):
        """fingerprint 가 일치하면 read_docs_index_cache 가 entries 리스트를 반환한다."""
        doc_sources = self._get_doc_sources()
        docs_index_cache = self._get_docs_index_cache()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# Plan\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            docs_build_cmd.rebuild_docs_index_cache(root)

            result = docs_index_cache.read_docs_index_cache(meta)
            self.assertIsNotNone(result, "Cache should hit when fingerprint matches")
            self.assertIsInstance(result, list)

    def test_schema_v1_cache_is_invalidated(self):
        """schema_version=1 payload 는 read_docs_index_cache 가 None 을 반환한다."""
        docs_index_cache = self._get_docs_index_cache()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            meta = meta_paths.MetaPaths(root)

            # Write a manual v1 payload
            v1_payload = {
                "schema_version": 1,
                "root": str(root),
                "generated_at_ms": 0,
                "entries": [],
            }
            (root / ".vibelign" / "docs_index.json").write_text(
                json.dumps(v1_payload), encoding="utf-8"
            )

            result = docs_index_cache.read_docs_index_cache(meta)
            self.assertIsNone(result, "Schema v1 cache should be invalidated")

    def test_schema_v2_markdown_only_cache_is_invalidated(self):
        """txt/csv/json 지원 전 schema=2 캐시는 stale 처리해야 한다."""
        docs_index_cache = self._get_docs_index_cache()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            meta = meta_paths.MetaPaths(root)
            v2_payload = {
                "schema_version": 2,
                "root": str(root),
                "generated_at_ms": 0,
                "sources_fingerprint": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "allowlist": {"extra_source_roots": []},
                "entries": [],
            }
            (root / ".vibelign" / "docs_index.json").write_text(
                json.dumps(v2_payload), encoding="utf-8"
            )

            result = docs_index_cache.read_docs_index_cache(meta)
            self.assertIsNone(result, "Schema v2 markdown-only cache should be invalidated")

    def test_full_build_writes_extra_under_underscore_extra(self):
        """full build 시 extra source 는 _extra/ 아래, built-in 은 기존 경로에 기록된다."""
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# My Plan\n\nContent here.\n", encoding="utf-8"
            )
            (root / "PROJECT_CONTEXT.md").write_text(
                "# Session Handoff\n\nBuilt-in.\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            docs_build_cmd.build_docs_visual_cache(root)

            docs_visual = root / ".vibelign" / "docs_visual"
            # built-in stays at original path
            self.assertTrue(
                (docs_visual / "PROJECT_CONTEXT.md.json").exists(),
                "Built-in artifact should be at original path",
            )
            # extra goes under _extra/
            self.assertTrue(
                (docs_visual / "_extra" / ".omc" / "plans" / "plan.md.json").exists(),
                "Extra source artifact should be under _extra/",
            )
            # no nested hidden dir at top level
            self.assertFalse(
                (docs_visual / ".omc").exists(),
                "Should not create nested hidden dir .omc under docs_visual",
            )

    def test_single_doc_build_extra_uses_underscore_extra(self):
        """single-doc build 시 extra source 문서의 artifact 는 _extra/ 아래 생성된다."""
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# My Plan\n\nContent here.\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            docs_build_cmd.build_docs_visual_cache(root, ".omc/plans/plan.md")

            artifact = (
                root / ".vibelign" / "docs_visual" / "_extra" / ".omc" / "plans" / "plan.md.json"
            )
            self.assertTrue(artifact.exists(), f"Extra artifact should be at {artifact}")

    def test_single_doc_build_builtin_uses_original_path(self):
        """single-doc build 시 built-in 문서의 artifact 경로는 _extra/ 없이 기존 위치다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "PROJECT_CONTEXT.md").write_text(
                "# Session Handoff\n\nBuilt-in.\n", encoding="utf-8"
            )

            docs_build_cmd.build_docs_visual_cache(root, "PROJECT_CONTEXT.md")

            artifact = root / ".vibelign" / "docs_visual" / "PROJECT_CONTEXT.md.json"
            self.assertTrue(artifact.exists(), f"Built-in artifact should be at {artifact}")
            wrong_path = root / ".vibelign" / "docs_visual" / "_extra" / "PROJECT_CONTEXT.md.json"
            self.assertFalse(wrong_path.exists(), "Built-in artifact should NOT be under _extra/")


class OrderingFixTest(unittest.TestCase):
    """Phase 2 ordering bug fix: extra-sources walk runs before iter_markdown_files catchall."""

    def _get_docs_cache(self):
        return sys.modules["vibelign.core.docs_cache"]

    def _get_doc_sources(self):
        return sys.modules["vibelign.core.doc_sources"]

    def _get_meta_paths(self):
        return sys.modules["vibelign.core.meta_paths"]

    def test_non_hidden_extra_source_labeled_custom(self):
        """non-hidden 등록 extra source 는 category=Custom, source_root=<rel>으로 나타난다.

        이전에는 iter_markdown_files catchall 이 먼저 실행되어 category=Docs로 덮였다.
        ordering fix 후: Custom이 먼저 등록되고 seen에 들어가므로 catchall이 skip한다.
        """
        docs_cache = self._get_docs_cache()
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            # Use a non-hidden directory outside docs/ so no built-in category claims it.
            (root / "my_plans").mkdir()
            (root / "my_plans" / "sprint.md").write_text("# Sprint Plan\n", encoding="utf-8")

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, "my_plans")

            entries = docs_cache.build_docs_index(root)
            matching = [e for e in entries if "sprint.md" in e.path]

            self.assertEqual(len(matching), 1, "sprint.md should appear exactly once")
            self.assertEqual(
                matching[0].category,
                "Custom",
                f"Expected Custom, got {matching[0].category!r} — ordering bug may still be present",
            )
            self.assertEqual(matching[0].source_root, "my_plans")

    def test_builtin_plan_not_overwritten_when_extra_registered(self):
        """built-in Plan 파일이 extra source와 같은 dir에 있어도 Plan 카테고리를 유지한다."""
        docs_cache = self._get_docs_cache()
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
            (root / "docs" / "superpowers" / "plans" / "phase6.md").write_text(
                "# Phase 6 Plan\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, "docs/superpowers/plans")

            entries = docs_cache.build_docs_index(root)
            matching = [e for e in entries if "phase6.md" in e.path]

            self.assertEqual(len(matching), 1, "phase6.md should appear exactly once")
            self.assertEqual(
                matching[0].category,
                "Plan",
                "Built-in Plan category must win over Custom registration",
            )


class RustLiteralRegressionTest(unittest.TestCase):
    """Rust 소스에 doc_sources.json 문자열 리터럴이 등장하지 않는다 (회귀 방지)."""

    def test_docs_access_rs_has_no_doc_sources_json_literal(self):
        """docs_access.rs 코드(주석 제외)에 'doc_sources.json' 문자열이 없어야 한다."""
        target = ROOT / "vibelign-gui" / "src-tauri" / "src" / "docs_access.rs"
        self.assertTrue(target.exists(), f"Expected file not found: {target}")

        code_lines = []
        for line in target.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip()
            if stripped.startswith("//"):
                continue
            code_lines.append(line)

        code = "\n".join(code_lines)
        self.assertNotIn(
            "doc_sources.json",
            code,
            "docs_access.rs must not reference doc_sources.json in non-comment code",
        )

    def test_lib_rs_has_no_doc_sources_json_literal(self):
        """lib.rs 코드(주석 제외)에 'doc_sources.json' 문자열이 없어야 한다."""
        target = ROOT / "vibelign-gui" / "src-tauri" / "src" / "lib.rs"
        self.assertTrue(target.exists(), f"Expected file not found: {target}")

        code_lines = []
        for line in target.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip()
            if stripped.startswith("//"):
                continue
            code_lines.append(line)

        code = "\n".join(code_lines)
        self.assertNotIn(
            "doc_sources.json",
            code,
            "lib.rs must not reference doc_sources.json in non-comment code",
        )


class DocsEnhanceExtraSourceRoutingTest(unittest.TestCase):
    """run_vib_docs_enhance가 extra source 문서의 artifact를 _extra/ 경로에서 찾고 써야 한다."""

    def _get_doc_sources(self):
        return sys.modules["vibelign.core.doc_sources"]

    def _get_meta_paths(self):
        return sys.modules["vibelign.core.meta_paths"]

    def _install_ai_stub(self):
        stub = types.ModuleType("vibelign.core.docs_ai_enhance")

        def call_auto(_source_text):
            return {
                "fields": {
                    "tldr_one_liner": "stub one liner",
                    "key_rules": [],
                    "success_criteria": [],
                    "edge_cases": [],
                    "components": [],
                },
                "model": "stub-model",
                "provider": "stub",
                "tokens_input": 0,
                "tokens_output": 0,
                "cost_usd": 0.0,
            }

        stub.call_auto = call_auto
        sys.modules["vibelign.core.docs_ai_enhance"] = stub

    def test_enhance_extra_source_finds_and_writes_under_extra(self):
        """extra source 문서는 artifact가 _extra/ 아래 있으므로 enhance도 거기서 찾아야 한다."""
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# Extra Plan\n\nBody.\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            docs_build_cmd.build_docs_visual_cache(root, ".omc/plans/plan.md")
            extra_artifact = (
                root
                / ".vibelign"
                / "docs_visual"
                / "_extra"
                / ".omc"
                / "plans"
                / "plan.md.json"
            )
            self.assertTrue(
                extra_artifact.exists(),
                "precondition: build should place extra artifact under _extra/",
            )

            self._install_ai_stub()
            os.environ["VIBELIGN_PROJECT_ROOT"] = str(root)
            try:
                docs_build_cmd.run_vib_docs_enhance(
                    Namespace(path=".omc/plans/plan.md", json=False)
                )
            finally:
                os.environ.pop("VIBELIGN_PROJECT_ROOT", None)

            payload = json.loads(extra_artifact.read_text(encoding="utf-8"))
            self.assertIn(
                "ai_fields",
                payload,
                "enhance should merge ai_fields into the _extra/ artifact",
            )
            self.assertEqual(payload["ai_fields"]["model"], "stub-model")

            wrong_path = (
                root
                / ".vibelign"
                / "docs_visual"
                / ".omc"
                / "plans"
                / "plan.md.json"
            )
            self.assertFalse(
                wrong_path.exists(),
                "enhance must not create a built-in-path artifact for extra source",
            )

    def test_enhance_extra_source_accepts_windows_style_input(self):
        """CLI에서 Windows 역슬래시 경로로 들어와도 _extra/ artifact를 찾아야 한다."""
        doc_sources = self._get_doc_sources()
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / ".omc" / "plans").mkdir(parents=True)
            (root / ".omc" / "plans" / "plan.md").write_text(
                "# Extra Plan\n\nBody.\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            doc_sources.add(meta, ".omc/plans")

            docs_build_cmd.build_docs_visual_cache(root, ".omc/plans/plan.md")
            extra_artifact = (
                root
                / ".vibelign"
                / "docs_visual"
                / "_extra"
                / ".omc"
                / "plans"
                / "plan.md.json"
            )
            self.assertTrue(extra_artifact.exists())

            self._install_ai_stub()
            os.environ["VIBELIGN_PROJECT_ROOT"] = str(root)
            try:
                docs_build_cmd.run_vib_docs_enhance(
                    Namespace(path=".omc\\plans\\plan.md", json=False)
                )
            finally:
                os.environ.pop("VIBELIGN_PROJECT_ROOT", None)

            payload = json.loads(extra_artifact.read_text(encoding="utf-8"))
            self.assertEqual(payload["ai_fields"]["model"], "stub-model")

    def test_enhance_builtin_source_still_uses_original_path(self):
        """built-in 문서의 artifact 경로는 _extra/ 가 붙으면 안 된다 (regression guard)."""
        meta_paths = self._get_meta_paths()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir()
            (root / "PROJECT_CONTEXT.md").write_text(
                "# Session Handoff\n\nbody\n", encoding="utf-8"
            )

            meta = meta_paths.MetaPaths(root)
            _ = meta  # silence lint

            docs_build_cmd.build_docs_visual_cache(root, "PROJECT_CONTEXT.md")
            builtin_artifact = (
                root / ".vibelign" / "docs_visual" / "PROJECT_CONTEXT.md.json"
            )
            self.assertTrue(builtin_artifact.exists())

            self._install_ai_stub()
            os.environ["VIBELIGN_PROJECT_ROOT"] = str(root)
            try:
                docs_build_cmd.run_vib_docs_enhance(
                    Namespace(path="PROJECT_CONTEXT.md", json=False)
                )
            finally:
                os.environ.pop("VIBELIGN_PROJECT_ROOT", None)

            payload = json.loads(builtin_artifact.read_text(encoding="utf-8"))
            self.assertEqual(payload["ai_fields"]["model"], "stub-model")
            self.assertFalse(
                (
                    root
                    / ".vibelign"
                    / "docs_visual"
                    / "_extra"
                    / "PROJECT_CONTEXT.md.json"
                ).exists(),
                "built-in enhance must not spill into _extra/",
            )
