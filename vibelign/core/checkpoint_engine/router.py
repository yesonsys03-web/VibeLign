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


def create_checkpoint(
    root: Path,
    message: str,
    *,
    trigger: str | None = None,
    git_commit_sha: str | None = None,
    git_commit_message: str | None = None,
) -> CheckpointSummary | None:
    return get_checkpoint_engine().create_checkpoint(
        root,
        message,
        trigger=trigger,
        git_commit_sha=git_commit_sha,
        git_commit_message=git_commit_message,
    )


def list_checkpoints(root: Path) -> list[CheckpointSummary]:
    return get_checkpoint_engine().list_checkpoints(root)


def restore_checkpoint(root: Path, checkpoint_id: str) -> bool:
    return get_checkpoint_engine().restore_checkpoint(root, checkpoint_id)


def diff_checkpoints(
    root: Path, from_checkpoint_id: str, to_checkpoint_id: str
) -> dict[str, object]:
    engine = get_checkpoint_engine()
    return engine.diff_checkpoints(root, from_checkpoint_id, to_checkpoint_id)


def preview_restore(
    root: Path, checkpoint_id: str, relative_paths: list[str] | None = None
) -> dict[str, object]:
    engine = get_checkpoint_engine()
    return engine.preview_restore(root, checkpoint_id, relative_paths)


def restore_files(root: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
    engine = get_checkpoint_engine()
    return engine.restore_files(root, checkpoint_id, relative_paths)


def restore_suggestions(root: Path, checkpoint_id: str, cap: int = 5) -> dict[str, object]:
    engine = get_checkpoint_engine()
    return engine.restore_suggestions(root, checkpoint_id, cap)


def has_changes_since_checkpoint(root: Path, checkpoint_id: str) -> bool:
    return get_checkpoint_engine().has_changes_since_checkpoint(root, checkpoint_id)


def prune_checkpoints(
    root: Path, policy: RetentionPolicy = DEFAULT_RETENTION_POLICY
) -> dict[str, int]:
    return get_checkpoint_engine().prune_checkpoints(root, policy)


def apply_retention(root: Path) -> dict[str, object]:
    engine = get_checkpoint_engine()
    return engine.apply_retention(root)


def inspect_backup_db(root: Path) -> dict[str, object]:
    engine = get_checkpoint_engine()
    return engine.inspect_backup_db(root)


def maintain_backup_db(root: Path, *, apply: bool = False) -> dict[str, object]:
    engine = get_checkpoint_engine()
    return engine.maintain_backup_db(root, apply=apply)


def get_last_restore_error() -> str:
    return get_checkpoint_engine().get_last_restore_error()


def friendly_time(created_at: str) -> str:
    return get_checkpoint_engine().friendly_time(created_at)


# === ANCHOR: CHECKPOINT_ENGINE_ROUTER_END ===
