import importlib.util
import sys
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


class ExtractTldrTest(unittest.TestCase):
    def test_first_sentence_of_first_paragraph(self):
        lines = [
            "# Title",
            "",
            "첫 문장입니다. 두번째 문장도 있어요.",
            "",
            "## Section",
        ]
        result = docs_visualizer._extract_tldr_one_liner(lines)
        self.assertEqual(result, "첫 문장입니다.")

    def test_empty_document_returns_empty(self):
        self.assertEqual(docs_visualizer._extract_tldr_one_liner([]), "")

    def test_no_paragraph_only_headings(self):
        lines = ["# A", "## B", "## C"]
        self.assertEqual(docs_visualizer._extract_tldr_one_liner(lines), "")

    def test_ignores_code_block_and_list(self):
        lines = [
            "# Title",
            "",
            "```",
            "inside code",
            "```",
            "",
            "- list item",
            "",
            "진짜 요약 문장.",
        ]
        self.assertEqual(docs_visualizer._extract_tldr_one_liner(lines), "진짜 요약 문장.")


if __name__ == "__main__":
    unittest.main()
