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


class ExtractBulletSectionTest(unittest.TestCase):
    def test_key_rules_from_rule_heading(self):
        lines = [
            "# Doc",
            "",
            "## 핵심 규칙",
            "",
            "- 절대 금지 항목 A",
            "- 항상 지킬 것 B",
            "",
            "## 다른 섹션",
            "- 무관한 내용",
        ]
        rules = docs_visualizer._extract_bullet_section(
            lines, docs_visualizer.RULES_HEADING_RE
        )
        self.assertEqual(rules, ["절대 금지 항목 A", "항상 지킬 것 B"])

    def test_success_criteria_from_success_heading(self):
        lines = [
            "# Doc",
            "",
            "## Success Criteria",
            "- 테스트 100% 통과",
            "- 지연 < 1초",
        ]
        criteria = docs_visualizer._extract_bullet_section(
            lines, docs_visualizer.CRITERIA_HEADING_RE
        )
        self.assertEqual(criteria, ["테스트 100% 통과", "지연 < 1초"])

    def test_edge_cases_from_edge_heading(self):
        lines = [
            "# Doc",
            "",
            "## 예외 상황",
            "- 네트워크 끊김",
            "- 빈 입력",
        ]
        edges = docs_visualizer._extract_bullet_section(
            lines, docs_visualizer.EDGE_HEADING_RE
        )
        self.assertEqual(edges, ["네트워크 끊김", "빈 입력"])

    def test_returns_empty_when_no_matching_heading(self):
        lines = ["# Doc", "", "## 무관한 섹션", "- 내용"]
        self.assertEqual(
            docs_visualizer._extract_bullet_section(
                lines, docs_visualizer.RULES_HEADING_RE
            ),
            [],
        )


class ExtractComponentsTest(unittest.TestCase):
    def test_h2_with_first_sentence(self):
        lines = [
            "# Doc",
            "",
            "## 파서",
            "markdown 을 AST 로 변환합니다. 그리고 캐시합니다.",
            "",
            "## 렌더러",
            "AST 를 HTML 로 렌더합니다.",
        ]
        items = docs_visualizer._extract_components(lines)
        self.assertEqual(
            items,
            ["파서 — markdown 을 AST 로 변환합니다.", "렌더러 — AST 를 HTML 로 렌더합니다."],
        )

    def test_limits_to_six_items(self):
        lines = ["# Doc"]
        for i in range(10):
            lines += ["", f"## Section {i}", f"Summary {i}."]
        items = docs_visualizer._extract_components(lines)
        self.assertEqual(len(items), 6)

    def test_skips_h2_with_no_content(self):
        lines = [
            "# Doc",
            "",
            "## Empty",
            "",
            "## Has content",
            "진짜 내용.",
        ]
        items = docs_visualizer._extract_components(lines)
        self.assertEqual(items, ["Has content — 진짜 내용."])


if __name__ == "__main__":
    unittest.main()
