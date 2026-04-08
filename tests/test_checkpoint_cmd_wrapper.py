import unittest
from argparse import Namespace
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


if __name__ == "__main__":
    _ = unittest.main()
