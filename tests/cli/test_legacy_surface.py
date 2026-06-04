import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vibelign.cli.cli_base import MAIN_DESCRIPTION
from vibelign.cli.vib_cli import build_parser
from vibelign.commands.vib_plan_structure_cmd import run_vib_plan_structure


class LegacySurfaceTest(unittest.TestCase):
    def test_main_help_keeps_only_plan_structure_in_legacy_group(self) -> None:
        beginner_sections = MAIN_DESCRIPTION.split("고급 / legacy:", maxsplit=1)[0]

        self.assertNotIn("AI 수정 요청:", beginner_sections)
        self.assertNotIn("  patch", beginner_sections)
        self.assertNotIn("plan-structure", beginner_sections)
        self.assertIn("고급 / legacy:", MAIN_DESCRIPTION)
        self.assertNotIn("patch", MAIN_DESCRIPTION)
        self.assertIn("plan-structure", MAIN_DESCRIPTION)

    def test_formatted_help_keeps_patch_absent_and_plan_structure_legacy(self) -> None:
        help_text = build_parser().format_help()
        beginner_sections = help_text.split("고급 / legacy:", maxsplit=1)[0]

        self.assertNotIn("  patch", beginner_sections)
        self.assertNotIn("plan-structure", beginner_sections)
        self.assertIn("고급 / legacy:", help_text)
        self.assertNotIn("patch", help_text)
        self.assertIn("plan-structure", help_text)

    def test_vib_plan_structure_prints_legacy_notice_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = Path.cwd()
            try:
                import os

                os.chdir(root)
                with patch("vibelign.commands.vib_plan_structure_cmd.build_structure_plan") as mocked_plan:
                    mocked_plan.return_value = {
                        "id": "plan_demo",
                        "created_at": "2026-06-04T00:00:00Z",
                        "required_new_files": [],
                        "allowed_modifications": [],
                    }
                    output = StringIO()
                    with redirect_stdout(output):
                        run_vib_plan_structure(
                            SimpleNamespace(
                                feature=["OAuth", "인증"],
                                ai=False,
                                scope="",
                                json=False,
                            )
                        )
            finally:
                os.chdir(previous)

        self.assertIn("vib plan-structure는 내부 구조 계획용 legacy 기능이에요", output.getvalue())


if __name__ == "__main__":
    _ = unittest.main()
