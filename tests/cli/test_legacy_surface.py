import unittest

from vibelign.cli.cli_base import MAIN_DESCRIPTION
from vibelign.cli.vib_cli import build_parser


class LegacySurfaceTest(unittest.TestCase):
    def test_main_help_excludes_retired_legacy_commands(self) -> None:
        beginner_sections = MAIN_DESCRIPTION.split("고급 / legacy:", maxsplit=1)[0]

        self.assertNotIn("AI 수정 요청:", beginner_sections)
        self.assertNotIn("  patch", beginner_sections)
        self.assertNotIn("plan-structure", beginner_sections)
        self.assertNotIn("고급 / legacy:", MAIN_DESCRIPTION)
        self.assertNotIn("patch", MAIN_DESCRIPTION)
        self.assertNotIn("plan-structure", MAIN_DESCRIPTION)

    def test_formatted_help_excludes_retired_legacy_commands(self) -> None:
        help_text = build_parser().format_help()
        beginner_sections = help_text.split("고급 / legacy:", maxsplit=1)[0]

        self.assertNotIn("  patch", beginner_sections)
        self.assertNotIn("plan-structure", beginner_sections)
        self.assertNotIn("고급 / legacy:", help_text)
        self.assertNotIn("patch", help_text)
        self.assertNotIn("plan-structure", help_text)


if __name__ == "__main__":
    _ = unittest.main()
