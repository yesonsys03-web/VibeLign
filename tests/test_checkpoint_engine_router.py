import tempfile
import unittest
from pathlib import Path

from vibelign.core.checkpoint_engine.router import (
    create_checkpoint,
    get_checkpoint_engine,
    list_checkpoints,
    restore_checkpoint,
)
from vibelign.core.checkpoint_engine.rust_checkpoint_engine import RustCheckpointEngine
from vibelign.core.checkpoint_engine.shadow_runner import prepare_shadow_run


class CheckpointEngineRouterTest(unittest.TestCase):
    def test_default_engine_uses_python_checkpoint_engine(self):
        self.assertIsInstance(get_checkpoint_engine(), RustCheckpointEngine)

    def test_router_preserves_create_list_restore_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            _ = target.write_text("print('v1')\n", encoding="utf-8")
            first = create_checkpoint(root, "first checkpoint")
            self.assertIsNotNone(first)
            assert first is not None

            _ = target.write_text("print('v2')\n", encoding="utf-8")
            self.assertTrue(restore_checkpoint(root, first.checkpoint_id))

            checkpoints = list_checkpoints(root)
            self.assertEqual(len(checkpoints), 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "print('v1')\n")

    def test_shadow_runner_has_no_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = prepare_shadow_run(root, "checkpoint_create", {"message": "x"})

            self.assertFalse(result.enabled)
            self.assertEqual(result.operation, "checkpoint_create")
            self.assertFalse((root / ".vibelign").exists())


if __name__ == "__main__":
    _ = unittest.main()
