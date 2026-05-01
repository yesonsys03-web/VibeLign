# === ANCHOR: CHECKPOINT_ENGINE_PYTHON_ENGINE_START ===
from __future__ import annotations

from pathlib import Path

from vibelign.core import local_checkpoints
from vibelign.core.checkpoint_engine.contracts import CheckpointSummary, RetentionPolicy


class PythonCheckpointEngine:
    """Adapter for the current Python checkpoint implementation."""

    def create_checkpoint(
        self,
        root: Path,
        message: str,
        *,
        trigger: str | None = None,
        git_commit_sha: str | None = None,
        git_commit_message: str | None = None,
    ) -> CheckpointSummary | None:
        return local_checkpoints.create_checkpoint(
            root,
            message,
            trigger=trigger,
            git_commit_sha=git_commit_sha,
            git_commit_message=git_commit_message,
        )

    def list_checkpoints(self, root: Path) -> list[CheckpointSummary]:
        return local_checkpoints.list_checkpoints(root)

    def restore_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return local_checkpoints.restore_checkpoint(root, checkpoint_id)

    def diff_checkpoints(
        self, _root: Path, _from_checkpoint_id: str, _to_checkpoint_id: str
    ) -> dict[str, object]:
        raise RuntimeError("checkpoint diff is not available")

    def preview_restore(
        self, _root: Path, _checkpoint_id: str, _relative_paths: list[str] | None = None
    ) -> dict[str, object]:
        raise RuntimeError("checkpoint preview is not available")

    def restore_files(
        self, _root: Path, _checkpoint_id: str, _relative_paths: list[str]
    ) -> int:
        raise RuntimeError("selected checkpoint restore is not available")

    def restore_suggestions(
        self, _root: Path, _checkpoint_id: str, _cap: int = 5
    ) -> dict[str, object]:
        raise RuntimeError("checkpoint restore suggestions are not available")

    def has_changes_since_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return local_checkpoints.has_changes_since_checkpoint(root, checkpoint_id)

    def prune_checkpoints(
        self, root: Path, policy: RetentionPolicy = local_checkpoints.DEFAULT_RETENTION_POLICY
    ) -> dict[str, int]:
        return local_checkpoints.prune_checkpoints(root, policy)

    def apply_retention(self, root: Path) -> dict[str, object]:
        pruned = local_checkpoints.prune_checkpoints(
            root, local_checkpoints.DEFAULT_RETENTION_POLICY
        )
        return {"count": pruned["count"], "bytes": pruned["bytes"]}

    def inspect_backup_db(self, _root: Path) -> dict[str, object]:
        raise RuntimeError("Backup DB Viewer requires the Rust checkpoint engine")

    def maintain_backup_db(self, _root: Path, *, apply: bool = False) -> dict[str, object]:
        _ = apply
        raise RuntimeError("Backup DB maintenance requires the Rust checkpoint engine")

    def get_last_restore_error(self) -> str:
        return local_checkpoints.get_last_restore_error()

    def friendly_time(self, created_at: str) -> str:
        return local_checkpoints.friendly_time(created_at)


# === ANCHOR: CHECKPOINT_ENGINE_PYTHON_ENGINE_END ===
