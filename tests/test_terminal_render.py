import io
import importlib
import importlib.util
import unittest
from contextlib import redirect_stdout

from vibelign.terminal_render import (
    clack_info,
    clack_step,
    _severity_style,
    normalize_ai_output,
    print_ai_response,
)


class TerminalRenderTests(unittest.TestCase):
    def test_severity_style_distinguishes_danger_warning_success(self) -> None:
        self.assertEqual(_severity_style("전체 상태: 중지"), "bold red")
        self.assertEqual(_severity_style("전체 상태: 주의"), "bold yellow")
        self.assertEqual(_severity_style("전체 상태: 통과"), "bold green")
        self.assertEqual(
            _severity_style(
                "지금은 큰 위험이 없어 보여요. 다음 단계로 넘어가도 됩니다."
            ),
            "bold green",
        )
        self.assertIsNone(_severity_style("최근 바뀐 내용의 위험도: LOW"))

    def test_normalize_keeps_code_fence_content(self) -> None:
        text = """### 제목

\u2022 첫 항목
1) 둘째 항목

```py
\u2022 keep
1) keep
```
"""

        normalized = normalize_ai_output(text)

        self.assertIn("- 첫 항목", normalized)
        self.assertIn("1. 둘째 항목", normalized)
        self.assertIn("\u2022 keep", normalized)
        self.assertIn("1) keep", normalized)

    def test_normalize_preserves_blank_lines_inside_code_fence(self) -> None:
        text = """```python
print('a')


print('b')
```"""

        normalized = normalize_ai_output(text)

        self.assertIn("print('a')\n\n\nprint('b')", normalized)

    def test_plain_render_falls_back_without_rich(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_ai_response("### 제목\n\n- 항목", use_rich=False)

        self.assertIn("### 제목", buffer.getvalue())
        self.assertIn("- 항목", buffer.getvalue())

    def test_rich_render_converts_sections_without_raw_markdown(self) -> None:
        console_mod = importlib.util.find_spec("rich.console")
        if console_mod is None:
            self.skipTest("rich is not installed")

        Console = importlib.import_module("rich.console").Console
        console = Console(record=True, width=80)
        print_ai_response(
            "## 1. 한 줄 요약\n이 파일은 로그인 흐름을 처리합니다.\n\n## 2. 주요 기능을 쉬운 말로 설명\n- 인증 확인\n- 토큰 발급",
            console=console,
            use_rich=True,
        )
        rendered = console.export_text()

        self.assertIn("1. 한 줄 요약", rendered)
        self.assertIn("- 인증 확인", rendered)
        self.assertNotIn("## 1. 한 줄 요약", rendered)

    def test_rich_render_applies_severity_styles(self) -> None:
        console_mod = importlib.util.find_spec("rich.console")
        if console_mod is None:
            self.skipTest("rich is not installed")

        Console = importlib.import_module("rich.console").Console
        console = Console(record=True, width=80)
        print_ai_response(
            "## 상태\n전체 상태: 중지\n\n- 먼저 문제를 해결하는 게 좋아요.\n- 전체 상태: 통과",
            console=console,
            use_rich=True,
        )
        rendered = console.export_text(styles=True)

        self.assertIn("\x1b[1;31m전체 상태: 중지", rendered)
        self.assertIn(
            "\x1b[1;31m- \x1b[0m\x1b[1;31m먼저 문제를 해결하는 게 좋아요.", rendered
        )
        self.assertIn("\x1b[1;32m- \x1b[0m\x1b[1;32m전체 상태: 통과", rendered)

    def test_rich_render_does_not_overcolor_low_risk_info(self) -> None:
        console_mod = importlib.util.find_spec("rich.console")
        if console_mod is None:
            self.skipTest("rich is not installed")

        Console = importlib.import_module("rich.console").Console
        console = Console(record=True, width=100)
        print_ai_response(
            "## 다음\n- 지금은 큰 위험이 없어 보여요. 다음 단계로 넘어가도 됩니다.\n- 최근 바뀐 내용의 위험도: LOW",
            console=console,
            use_rich=True,
        )
        rendered = console.export_text(styles=True)

        self.assertIn(
            "\x1b[1;32m- \x1b[0m\x1b[1;32m지금은 큰 위험이 없어 보여요. 다음 단계로 넘어가도 됩니다.",
            rendered,
        )
        self.assertIn(
            "\x1b[1;36m- \x1b[0m\x1b[37m최근 바뀐 내용의 위험도: LOW", rendered
        )

    def test_clack_info_uses_severity_color_for_warning_message(self) -> None:
        console_mod = importlib.util.find_spec("rich.console")
        if console_mod is None:
            self.skipTest("rich is not installed")

        Console = importlib.import_module("rich.console").Console
        console = Console(record=True, width=100)
        clack_info("문제가 있으면 먼저 해결하세요.", console=console)
        rendered = console.export_text(styles=True)

        self.assertIn("\x1b[1;31m• 문제가 있으면 먼저 해결하세요.", rendered)

    def test_clack_step_keeps_default_color_for_neutral_message(self) -> None:
        console_mod = importlib.util.find_spec("rich.console")
        if console_mod is None:
            self.skipTest("rich is not installed")

        Console = importlib.import_module("rich.console").Console
        console = Console(record=True, width=100)
        clack_step("프로젝트 상태를 확인하는 중...", console=console)
        rendered = console.export_text(styles=True)

        self.assertIn("\x1b[36m◌ 프로젝트 상태를 확인하는 중...", rendered)


if __name__ == "__main__":
    unittest.main()
