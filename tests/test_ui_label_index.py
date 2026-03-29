import tempfile
import unittest
from pathlib import Path

from vibelign.core.patch_suggester import tokenize
from vibelign.core.ui_label_index import build_ui_label_index, score_boost_for_ui_labels


class UiLabelIndexTest(unittest.TestCase):
    def test_indexes_aria_placeholder_ko_jsx(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "src" / "Page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text(
                'import React from "react";\n'
                "export function Page() {\n"
                '  return (\n'
                '    <button aria-label="로그인 하기" placeholder="이메일 입력" '
                'title="Sign in" alt="아이콘">\n'
                "      <span>확인하기</span>\n"
                "    </button>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )
            payload = build_ui_label_index(root)
        labels = payload.get("labels")
        self.assertIsInstance(labels, dict)
        assert isinstance(labels, dict)
        self.assertIn("로그인 하기", labels)
        self.assertIn("이메일 입력", labels)
        self.assertIn("Sign in", labels)
        self.assertIn("아이콘", labels)
        self.assertIn("확인하기", labels)

    def test_score_boost_matches_korean_two_char_token(self) -> None:
        index = {
            "버튼": [{"path": "a.tsx", "line": 1}],
        }
        tokens = tokenize("버튼 색")
        boost, reasons = score_boost_for_ui_labels("a.tsx", tokens, index)
        self.assertGreaterEqual(boost, 4)
        self.assertTrue(any("버튼" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
