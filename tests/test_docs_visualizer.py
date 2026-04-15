import importlib.util
import sys
import tempfile
import types
import unittest
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
_load_module("vibelign.core.docs_cache", ROOT / "vibelign" / "core" / "docs_cache.py")
docs_visualizer = _load_module(
    "vibelign.core.docs_visualizer", ROOT / "vibelign" / "core" / "docs_visualizer.py"
)


class DocsVisualizerTest(unittest.TestCase):
    def test_authored_mermaid_is_preserved_and_marked_authored(self):
        content = """# Demo Title

Intro summary paragraph.

## Diagram

```mermaid
flowchart TD
  A[Start] --> B[Done]
```
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "demo.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(artifact.title, "Demo Title")
            self.assertEqual(len(artifact.diagram_blocks), 1)
            self.assertEqual(artifact.diagram_blocks[0].provenance, "authored")
            self.assertEqual(
                artifact.diagram_blocks[0].generator, "authored-mermaid-v1"
            )

    def test_readme_without_mermaid_generates_heading_mindmap(self):
        content = """# Annotation Translator

Short overview.

## 설치 가이드

설치 설명.

## 사용법

사용 설명.

## FAQ

질문 모음.
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "README.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(len(artifact.diagram_blocks), 1)
            diagram = artifact.diagram_blocks[0]
            self.assertEqual(diagram.provenance, "heuristic")
            self.assertEqual(diagram.generator, "heading-mindmap-v1")
            self.assertEqual(diagram.confidence, "medium")
            self.assertIn("mindmap", diagram.source)

    def test_ordered_steps_generate_step_flow(self):
        content = """# Install Guide

Quick setup.

1. Copy files
2. Add API key
3. Restart Harmony
4. Verify output
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "guide.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(len(artifact.diagram_blocks), 1)
            diagram = artifact.diagram_blocks[0]
            self.assertEqual(diagram.generator, "step-flow-v1")
            self.assertEqual(diagram.confidence, "high")
            self.assertIn("flowchart TD", diagram.source)
            self.assertIn("S1", diagram.source)

    def test_component_doc_generates_structural_summary(self):
        content = """# Module Layout

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| configure.js | 진입점 |
| src/main.py | 처리 |
| docs/guide/README.md | 안내 |
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "architecture.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(len(artifact.diagram_blocks), 1)
            diagram = artifact.diagram_blocks[0]
            self.assertEqual(diagram.generator, "component-flow-v1")
            self.assertIn("structural summary", " ".join(diagram.warnings))
            self.assertIn("subgraph DOC", diagram.source)
            self.assertNotIn(" --> ", diagram.source)

    def test_wiki_index_prefers_heading_mindmap_over_link_component_summary(self):
        content = """# VibeLign Wiki

## Start Here

- [Project Overview](./project-overview.md)
- [Getting Started](./getting-started.md)

## What VibeLign Is

Overview text.

## Best Canonical Sources

- [`../../README.md`](../../README.md)
- [`../../AGENTS.md`](../../AGENTS.md)

## How To Use This Wiki

Use the linked docs as source of truth.
"""
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs" / "wiki"
            docs_dir.mkdir(parents=True)
            target = docs_dir / "index.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(len(artifact.diagram_blocks), 1)
            diagram = artifact.diagram_blocks[0]
            self.assertEqual(diagram.generator, "heading-mindmap-v1")
            self.assertEqual(diagram.provenance, "heuristic")
            self.assertIn("mindmap", diagram.source)

    def test_invalid_authored_mermaid_falls_back_to_heuristic(self):
        content = """# Invalid Diagram Doc

## Overview

Short note.

```mermaid
hello world
```

## Usage

More context.

## FAQ

Extra section.
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "README.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(len(artifact.diagram_blocks), 1)
            self.assertEqual(artifact.diagram_blocks[0].provenance, "heuristic")
            self.assertTrue(
                any(
                    "invalid authored mermaid block ignored" in warning
                    for warning in artifact.warnings
                )
            )

    def test_code_fence_headings_are_not_treated_as_real_sections(self):
        content = """# Spec Doc

## Real Section

```python
# Fake Heading
print('hello')
```
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "spec.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(
                [section.title for section in artifact.sections],
                ["Spec Doc", "Real Section"],
            )

    def test_illustrative_mermaid_examples_do_not_override_heuristic(self):
        content = """# Heuristic Mermaid 자동 생성 설계

## 핵심 변경

설계 요약.

### Mermaid 템플릿

```mermaid
flowchart TD
  A[Start] --> B[Done]
```

## signal 추출 규칙

설명.

## diagram type 별 규칙

설명.
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "design.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(len(artifact.diagram_blocks), 1)
            self.assertEqual(artifact.diagram_blocks[0].provenance, "heuristic")
            self.assertEqual(artifact.diagram_blocks[0].generator, "heading-mindmap-v1")
            self.assertTrue(
                any(
                    "illustrative mermaid example ignored" in warning
                    for warning in artifact.warnings
                )
            )

    def test_low_confidence_doc_skips_diagram(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "notes.md"
            target.write_text(
                "just a loose thought without structure", encoding="utf-8"
            )

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(artifact.diagram_blocks, [])
            self.assertIn(
                "auto_diagram_skipped: low confidence (score<4)", artifact.warnings
            )

    def test_huge_doc_keeps_authored_diagram(self):
        filler = "\n".join(f"line {index}" for index in range(1300))
        content = f"# Huge\n\n```mermaid\nflowchart TD\n  A[Start] --> B[Done]\n```\n\n{filler}\n"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "huge.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(len(artifact.diagram_blocks), 1)
            self.assertEqual(artifact.diagram_blocks[0].provenance, "authored")
            self.assertFalse(
                any(
                    "auto_diagram_skipped_huge_doc" in warning
                    for warning in artifact.warnings
                )
            )

    def test_huge_doc_without_authored_skips_heuristic(self):
        filler = "\n".join(f"line {index}" for index in range(1300))
        content = f"# Huge\n\n## Intro\n\nAlpha\n\n## Usage\n\nBeta\n\n{filler}\n"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "huge.md"
            target.write_text(content, encoding="utf-8")

            artifact = docs_visualizer.visualize_markdown_file(target)

            self.assertEqual(artifact.diagram_blocks, [])
            self.assertTrue(
                any(
                    "auto_diagram_skipped_huge_doc" in warning
                    for warning in artifact.warnings
                )
            )

    def test_crlf_and_bom_produce_same_diagram_source(self):
        base = "# Install Guide\n\n1. Copy files\n2. Add API key\n3. Restart\n"
        with tempfile.TemporaryDirectory() as tmp:
            lf = Path(tmp) / "lf.md"
            crlf = Path(tmp) / "crlf.md"
            lf.write_text(base, encoding="utf-8")
            crlf.write_bytes(
                b"\xef\xbb\xbf" + base.replace("\n", "\r\n").encode("utf-8")
            )

            first = docs_visualizer.visualize_markdown_file(lf)
            second = docs_visualizer.visualize_markdown_file(crlf)

            self.assertEqual(
                first.diagram_blocks[0].source, second.diagram_blocks[0].source
            )
            self.assertEqual(
                first.diagram_blocks[0].generator, second.diagram_blocks[0].generator
            )

    def test_same_input_produces_same_structured_output(self):
        content = "# Stable\n\n## Setup\n\n1. Alpha\n2. Beta\n3. Gamma\n"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "stable.md"
            target.write_text(content, encoding="utf-8")

            first = docs_visualizer.visualize_markdown_file(target).to_dict()
            second = docs_visualizer.visualize_markdown_file(target).to_dict()

            self.assertEqual(first, second)

    def test_non_utf8_input_returns_clear_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bad.md"
            target.write_bytes(b"\xff\xfe\x00\x00")

            with self.assertRaises(ValueError) as ctx:
                docs_visualizer.visualize_markdown_file(target)

            self.assertIn("UTF-8 markdown", str(ctx.exception))
