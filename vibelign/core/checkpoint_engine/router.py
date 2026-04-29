# === ANCHOR: CHECKPOINT_ENGINE_ROUTER_START ===
from __future__ import annotations

from pathlib import Path

from vibelign.core.local_checkpoints import DEFAULT_RETENTION_POLICY
from vibelign.core.checkpoint_engine.contracts import (
    CheckpointEngine,
    CheckpointSummary,
    RetentionPolicy,
)
from vibelign.core.checkpoint_engine.rust_checkpoint_engine import RustCheckpointEngine

_DEFAULT_ENGINE: CheckpointEngine = RustCheckpointEngine()


def get_checkpoint_engine() -> CheckpointEngine:
    return _DEFAULT_ENGINE


def create_checkpoint(root: Path, message: str) -> CheckpointSummary | None:
    return get_checkpoint_engine().create_checkpoint(root, message)


def list_checkpoints(root: Path) -> list[CheckpointSummary]:
    return get_checkpoint_engine().list_checkpoints(root)


def restore_checkpoint(root: Path, checkpoint_id: str) -> bool:
    return get_checkpoint_engine().restore_checkpoint(root, checkpoint_id)


def has_changes_since_checkpoint(root: Path, checkpoint_id: str) -> bool:
    return get_checkpoint_engine().has_changes_since_checkpoint(root, checkpoint_id)


def prune_checkpoints(
    root: Path, policy: RetentionPolicy = DEFAULT_RETENTION_POLICY
) -> dict[str, int]:
    return get_checkpoint_engine().prune_checkpoints(root, policy)


def get_last_restore_error() -> str:
    return get_checkpoint_engine().get_last_restore_error()


def friendly_time(created_at: str) -> str:
    return get_checkpoint_engine().friendly_time(created_at)


# === ANCHOR: CHECKPOINT_ENGINE_ROUTER_END ===
