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
_load_module("vibelign.core.docs_cache", ROOT / "vibelign" / "core" / "docs_cache.py")
_load_module(
    "vibelign.core.docs_visualizer", ROOT / "vibelign" / "core" / "docs_visualizer.py"
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
