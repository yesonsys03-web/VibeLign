# === ANCHOR: CHECKPOINT_ENGINE_PYTHON_ENGINE_START ===
from __future__ import annotations

from pathlib import Path

from vibelign.core import local_checkpoints
from vibelign.core.checkpoint_engine.contracts import CheckpointSummary, RetentionPolicy


class PythonCheckpointEngine:
    """Adapter for the current Python checkpoint implementation."""

    def create_checkpoint(self, root: Path, message: str) -> CheckpointSummary | None:
        return local_checkpoints.create_checkpoint(root, message)

    def list_checkpoints(self, root: Path) -> list[CheckpointSummary]:
        return local_checkpoints.list_checkpoints(root)

    def restore_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return local_checkpoints.restore_checkpoint(root, checkpoint_id)

    def has_changes_since_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return local_checkpoints.has_changes_since_checkpoint(root, checkpoint_id)

    def prune_checkpoints(
        self, root: Path, policy: RetentionPolicy = local_checkpoints.DEFAULT_RETENTION_POLICY
    ) -> dict[str, int]:
        return local_checkpoints.prune_checkpoints(root, policy)

    def get_last_restore_error(self) -> str:
        return local_checkpoints.get_last_restore_error()

    def friendly_time(self, created_at: str) -> str:
        return local_checkpoints.friendly_time(created_at)


# === ANCHOR: CHECKPOINT_ENGINE_PYTHON_ENGINE_END ===
