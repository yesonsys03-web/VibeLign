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
    def create_checkpoint(self, root: Path, message: str) -> CheckpointSummary | None: ...

    def list_checkpoints(self, root: Path) -> list[CheckpointSummary]: ...

    def restore_checkpoint(self, root: Path, checkpoint_id: str) -> bool: ...

    def has_changes_since_checkpoint(self, root: Path, checkpoint_id: str) -> bool: ...

    def prune_checkpoints(
        self, root: Path, policy: RetentionPolicy = DEFAULT_RETENTION_POLICY
    ) -> dict[str, int]: ...

    def get_last_restore_error(self) -> str: ...

    def friendly_time(self, created_at: str) -> str: ...


# === ANCHOR: CHECKPOINT_ENGINE_CONTRACTS_END ===
