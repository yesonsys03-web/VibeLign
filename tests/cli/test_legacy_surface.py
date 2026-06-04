import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vibelign.cli.cli_base import MAIN_DESCRIPTION
from vibelign.commands.vib_patch_cmd import run_vib_patch
from vibelign.commands.vib_plan_structure_cmd import run_vib_plan_structure


class LegacySurfaceTest(unittest.TestCase):
    def test_main_help_keeps_patch_and_plan_structure_out_of_beginner_groups(self) -> None:
        beginner_sections = MAIN_DESCRIPTION.split("고급 / legacy:", maxsplit=1)[0]

        self.assertNotIn("AI 수정 요청:", beginner_sections)
        self.assertNotIn("  patch", beginner_sections)
        self.assertNotIn("plan-structure", beginner_sections)
        self.assertIn("고급 / legacy:", MAIN_DESCRIPTION)
        self.assertIn("patch", MAIN_DESCRIPTION)
        self.assertIn("plan-structure", MAIN_DESCRIPTION)

    def test_vib_patch_prints_legacy_notice_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = Path.cwd()
            try:
                import os

                os.chdir(root)
                with patch("vibelign.commands.vib_patch_cmd._build_patch_data") as mocked_build:
                    mocked_build.return_value = {
                        "preview": None,
                        "patch_plan": {"target_file": "app.py"},
                    }
                    with patch("vibelign.commands.vib_patch_cmd._output_helpers") as helpers:
                        helpers.return_value.emit_patch_result.return_value = None
                        output = StringIO()
                        with redirect_stdout(output):
                            run_vib_patch(
                                SimpleNamespace(
                                    apply_strict=None,
                                    request=["로그인", "수정"],
                                    ai=False,
                                    json=False,
                                    preview=False,
                                    lazy_fanout=False,
                                    write_report=False,
                                    copy=False,
                                )
                            )
            finally:
                os.chdir(previous)

        self.assertIn("vib patch는 legacy 기능이에요", output.getvalue())

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
