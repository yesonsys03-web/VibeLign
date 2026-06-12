import os
import unittest
import importlib
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_guard_cmd import GuardArgs, run_vib_guard


_render_markdown = importlib.import_module(
    "vibelign.commands.vib_guard_cmd"
)._render_markdown
_verdict_tier = importlib.import_module("vibelign.commands.vib_guard_cmd")._verdict_tier


class VerdictTierTest(unittest.TestCase):
    """위반 채널과 위생 채널의 분리(2026-06-12) — 위반 0이면 위생 누적만으로 stop 금지."""

    def test_hygiene_only_fail_is_prepare_not_stop(self):
        # 알람앱 케이스: 새 파일 앵커 미설정 감점 누적으로 status=fail 이지만 위반 0
        self.assertEqual(_verdict_tier([], [], "LOW", "pass", "fail"), "prepare")

    def test_clean_project_passes(self):
        self.assertEqual(_verdict_tier([], [], "LOW", "pass", "pass"), "pass")

    def test_any_violation_is_stop(self):
        self.assertEqual(_verdict_tier(["src/a.py"], [], "LOW", "pass", "fail"), "stop")
        self.assertEqual(_verdict_tier([], ["src/b.py"], "LOW", "pass", "warn"), "stop")
        self.assertEqual(_verdict_tier([], [], "HIGH", "pass", "pass"), "stop")
        self.assertEqual(_verdict_tier([], [], "LOW", "fail", "fail"), "stop")


class VibGuardRenderTest(unittest.TestCase):
    def test_render_markdown_contains_status_and_next_steps(self):
        markdown = _render_markdown(
            {
                "status": "warn",
                "strict": False,
                "project_score": 68,
                "project_status": "Caution",
                "change_risk_level": "MEDIUM",
                "summary": "구조 위험이 조금 있습니다.",
                "recommendations": ["vib anchor --suggest", "vib guard --strict"],
                "protected_violations": [],
                "anchor_violations": [],
                "explain": {
                    "files": [{"path": "app.py", "status": "modified", "kind": "logic"}]
                },
                "planning": {
                    "status": "planning_exempt",
                    "strict": False,
                    "active_plan_id": None,
                    "summary": "현재 변경은 문서만 수정하므로 별도 기획 없이 진행 가능한 범위입니다.",
                    "changed_files": ["docs/README.md"],
                    "required_reasons": [],
                    "deviations": [],
                    "exempt_reasons": ["docs_only"],
                },
            }
        )
        # verdict 부재(구버전 데이터) → status 에서 보수적 유도: warn → prepare
        self.assertIn("전체 상태: 준비 필요", markdown)
        self.assertIn("다음 AI 작업 전에 아래 권장 항목을 준비하면 더 안전해져요", markdown)
        self.assertIn("## 다음에 하면 좋은 일", markdown)
        self.assertIn("구조 위험이 조금 있습니다.", markdown)
        self.assertIn("`app.py`", markdown)
        self.assertIn(
            "문서만 수정하므로 별도 기획 없이 진행 가능한 범위입니다.", markdown
        )

    def test_run_vib_guard_uses_rich_renderer_for_text_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "vibelign.commands.vib_guard_cmd.print_ai_response"
                ) as mocked:
                    run_vib_guard(
                        cast(
                            GuardArgs,
                            cast(
                                object,
                                SimpleNamespace(
                                    json=False,
                                    strict=False,
                                    since_minutes=120,
                                    write_report=False,
                                ),
                            ),
                        )
                    )
                    mocked.assert_called_once()
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
