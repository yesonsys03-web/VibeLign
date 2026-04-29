import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_checkpoint_cmd import create_for_cli, list_for_cli
from vibelign.core.local_checkpoints import CheckpointSummary


class VibCheckpointRustCliTest(unittest.TestCase):
    def test_create_uses_router_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.commands.vib_checkpoint_cmd.create_checkpoint",
                return_value=None,
            ) as mocked_router:
                _ = create_for_cli(root, "message")

            mocked_router.assert_called_once()

    def test_create_returns_router_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = CheckpointSummary("cp1", "cp1", "message", 1)
            with patch(
                "vibelign.commands.vib_checkpoint_cmd.create_checkpoint",
                return_value=summary,
            ) as mocked_router:
                result, warning = create_for_cli(root, "message")

            mocked_router.assert_called_once()
            self.assertEqual(result, summary)
            self.assertIsNone(warning)

    def test_list_uses_router_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoints = [CheckpointSummary("cp1", "cp1", "message", 1)]
            with patch(
                "vibelign.commands.vib_checkpoint_cmd.list_checkpoints",
                return_value=checkpoints,
            ) as mocked_router:
                result, warning = list_for_cli(root)

            mocked_router.assert_called_once()
            self.assertEqual(result, checkpoints)
            self.assertIsNone(warning)


if __name__ == "__main__":
    _ = unittest.main()
