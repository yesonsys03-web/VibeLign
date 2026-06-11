"""watch_rules: 일반 소스 파일 줄 수 증가 감시."""

import unittest
from pathlib import Path

from vibelign.core.watch_rules import classify_event


class WatchRulesGenericGrowthTest(unittest.TestCase):
    def test_non_entry_file_large_growth_emits_high(self) -> None:
        path = Path("FeatureStuff.tsx")
        text = "export const x = 1\n" * 1100
        warns = classify_event(path, text, old_lines=100, new_lines=1100, strict=False)
        levels = [w["level"] for w in warns]
        self.assertIn("HIGH", levels)
        self.assertTrue(any("FeatureStuff.tsx" in w["message"] for w in warns))

    def test_non_entry_file_moderate_growth_emits_warn(self) -> None:
        path = Path("Widget.tsx")
        text = "//\n" * 720
        warns = classify_event(path, text, old_lines=500, new_lines=720, strict=False)
        levels = [w["level"] for w in warns]
        self.assertIn("WARN", levels)

    def test_entry_file_uses_entry_thresholds_not_generic_only(self) -> None:
        path = Path("main.ts")
        text = "//\n" * 250
        warns = classify_event(path, text, old_lines=50, new_lines=250, strict=False)
        messages = " ".join(w["message"] for w in warns)
        self.assertIn("main.ts", messages)

    def test_vib_cli_file_uses_entry_thresholds(self) -> None:
        path = Path("vib_cli.py")
        text = "#\n" * 250
        warns = classify_event(path, text, old_lines=50, new_lines=250, strict=False)
        messages = " ".join(w["message"] for w in warns)
        self.assertIn("vib_cli.py", messages)

    def test_mcp_server_file_uses_entry_thresholds(self) -> None:
        path = Path("mcp_server.py")
        text = "#\n" * 250
        warns = classify_event(path, text, old_lines=50, new_lines=250, strict=False)
        messages = " ".join(w["message"] for w in warns)
        self.assertIn("mcp_server.py", messages)

    def test_markdown_doc_skips_anchor_warning(self) -> None:
        # 기획안 등 명세 문서는 코드가 아니다 — 앵커 없음 경고를 내면 안 된다.
        path = Path("plans/알람앱-만들기.md")
        text = "본문 줄\n" * 200
        warns = classify_event(path, text, old_lines=None, new_lines=200, strict=False)
        messages = " ".join(w["message"] for w in warns)
        self.assertNotIn("앵커가 없습니다", messages)

    def test_code_file_still_gets_anchor_warning(self) -> None:
        path = Path("service.py")
        text = "x = 1\n" * 200
        warns = classify_event(path, text, old_lines=None, new_lines=200, strict=False)
        messages = " ".join(w["message"] for w in warns)
        self.assertIn("앵커가 없습니다", messages)


if __name__ == "__main__":
    _ = unittest.main()
