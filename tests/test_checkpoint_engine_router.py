import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.checkpoint_engine.router import (
    create_checkpoint,
    get_checkpoint_engine,
    inspect_backup_db,
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

    def test_router_inspect_backup_db_delegates(self):
        class FakeEngine:
            def inspect_backup_db(self, root: Path) -> dict[str, object]:
                return {"root": str(root), "db_exists": False}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.router.get_checkpoint_engine",
                return_value=FakeEngine(),
            ):
                report = inspect_backup_db(root)

        self.assertFalse(report["db_exists"])
        self.assertEqual(report["root"], str(root))


if __name__ == "__main__":
    _ = unittest.main()
