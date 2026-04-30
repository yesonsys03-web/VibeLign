import unittest
from argparse import Namespace
from dataclasses import dataclass
from typing import cast
from unittest.mock import patch

from vibelign.commands.checkpoint_cmd import run_checkpoint


class CheckpointCmdWrapperTest(unittest.TestCase):
    def test_run_checkpoint_delegates_to_vib_checkpoint(self) -> None:
        with patch("vibelign.commands.checkpoint_cmd.run_vib_checkpoint") as mocked:
            run_checkpoint(Namespace(message=["legacy", "save"]))

        mocked.assert_called_once()
        delegated_args = cast(Namespace, mocked.call_args.args[0])
        self.assertEqual(delegated_args.message, ["legacy", "save"])
        self.assertFalse(delegated_args.json)

    def test_history_auto_backup_message_hides_internal_sha(self) -> None:
        from vibelign.commands.vib_history_cmd import _clean_msg

        label = _clean_msg(
            "vibelign: auto backup after commit abc1234",
            "post_commit",
            "feat: login form",
        )

        self.assertEqual(label, "코드 저장 후 자동 백업 - feat: login form")
        self.assertNotIn("abc1234", label)

    def test_undo_filters_safe_restore_checkpoints(self) -> None:
        from vibelign.commands.vib_undo_cmd import _visible_checkpoints

        @dataclass
        class _Checkpoint:
            trigger: str | None
            message: str = ""
            git_commit_message: str | None = None

        visible = _visible_checkpoints([_Checkpoint("safe_restore"), _Checkpoint(None)])

        self.assertEqual(len(visible), 1)
        self.assertIsNone(visible[0].trigger)


if __name__ == "__main__":
    _ = unittest.main()
