import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_docs_visualizer_module():
    path = (
        Path(__file__).resolve().parents[1] / "vibelign" / "core" / "docs_visualizer.py"
    )
    spec = importlib.util.spec_from_file_location("test_docs_visualizer_module", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


docs_visualizer = _load_docs_visualizer_module()


class DocsVisualizerTest(unittest.TestCase):
    def test_generates_visual_artifact_from_normal_doc(self):
        content = """# Demo Title

Intro summary paragraph.

## Checklist

- [ ] first action
- [x] done action

## Warnings

⚠ keep fallback path intact

## Diagram

```mermaid
flowchart TD
  A[Start] --> B[Done]
```
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "demo.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(artifact.title, "Demo Title")
            self.assertEqual(artifact.summary, "Intro summary paragraph.")
            self.assertEqual(len(artifact.sections), 4)
            self.assertEqual(
                [item.text for item in artifact.action_items],
                ["first action", "done action"],
            )
            self.assertEqual(
                [item.checked for item in artifact.action_items], [False, True]
            )
            self.assertEqual(len(artifact.diagram_blocks), 1)
            self.assertEqual(artifact.diagram_blocks[0].kind, "mermaid")
            self.assertTrue(
                any("fallback path" in warning for warning in artifact.warnings)
            )
            self.assertTrue(artifact.source_hash)

    def test_empty_doc_falls_back_to_filename_and_empty_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "empty-doc.md"
            target.write_text("\n\n", encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(artifact.title, "empty doc")
            self.assertEqual(artifact.summary, "Empty markdown document.")
            self.assertEqual(artifact.sections, [])

    def test_same_input_produces_same_structured_output(self):
        content = "# Stable\n\nHello world.\n\n## Next Step\n- ship it\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "stable.md"
            target.write_text(content, encoding="utf-8")

            first = docs_visualizer.visualize_markdown_file(target).to_dict()
            second = docs_visualizer.visualize_markdown_file(target).to_dict()

            self.assertEqual(first, second)

    def test_non_utf8_input_returns_clear_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "bad.md"
            target.write_bytes(b"\xff\xfe\x00\x00")

            with self.assertRaises(ValueError) as ctx:
                docs_visualizer.visualize_markdown_file(target)

            self.assertIn("UTF-8 markdown", str(ctx.exception))
