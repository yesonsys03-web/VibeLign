# === ANCHOR: CHECKPOINT_ENGINE_CONTRACTS_START ===
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vibelign.core.local_checkpoints import (
    DEFAULT_RETENTION_POLICY,
    CheckpointSummary,
    RetentionPolicy,
)

__all__ = ["CheckpointEngine", "CheckpointSummary", "RetentionPolicy"]


class CheckpointEngine(Protocol):
    def create_checkpoint(
        self,
        root: Path,
        message: str,
        *,
        trigger: str | None = None,
        git_commit_sha: str | None = None,
        git_commit_message: str | None = None,
    ) -> CheckpointSummary | None: ...

    def list_checkpoints(self, root: Path) -> list[CheckpointSummary]: ...

    def restore_checkpoint(self, root: Path, checkpoint_id: str) -> bool: ...

    def diff_checkpoints(
        self, root: Path, from_checkpoint_id: str, to_checkpoint_id: str
    ) -> dict[str, object]: ...

    def preview_restore(
        self, root: Path, checkpoint_id: str, relative_paths: list[str] | None = None
    ) -> dict[str, object]: ...

    def restore_files(
        self, root: Path, checkpoint_id: str, relative_paths: list[str]
    ) -> int: ...

    def restore_suggestions(
        self, root: Path, checkpoint_id: str, cap: int = 5
    ) -> dict[str, object]: ...

    def has_changes_since_checkpoint(self, root: Path, checkpoint_id: str) -> bool: ...

    def prune_checkpoints(
        self, root: Path, policy: RetentionPolicy = DEFAULT_RETENTION_POLICY
    ) -> dict[str, int]: ...

    def get_last_restore_error(self) -> str: ...

    def friendly_time(self, created_at: str) -> str: ...

    def apply_retention(self, root: Path) -> dict[str, object]: ...

    def inspect_backup_db(self, root: Path) -> dict[str, object]: ...

    def maintain_backup_db(self, root: Path, *, apply: bool = False) -> dict[str, object]: ...


# === ANCHOR: CHECKPOINT_ENGINE_CONTRACTS_END ===
