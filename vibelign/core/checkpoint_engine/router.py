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


def diff_checkpoints(
    root: Path, from_checkpoint_id: str, to_checkpoint_id: str
) -> dict[str, object]:
    engine = get_checkpoint_engine()
    if hasattr(engine, "diff_checkpoints"):
        return engine.diff_checkpoints(root, from_checkpoint_id, to_checkpoint_id)  # type: ignore[attr-defined]
    raise RuntimeError("checkpoint diff is not available")


def preview_restore(
    root: Path, checkpoint_id: str, relative_paths: list[str] | None = None
) -> dict[str, object]:
    engine = get_checkpoint_engine()
    if hasattr(engine, "preview_restore"):
        return engine.preview_restore(root, checkpoint_id, relative_paths)  # type: ignore[attr-defined]
    raise RuntimeError("checkpoint preview is not available")


def restore_files(root: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
    engine = get_checkpoint_engine()
    if hasattr(engine, "restore_files"):
        return engine.restore_files(root, checkpoint_id, relative_paths)  # type: ignore[attr-defined]
    raise RuntimeError("selected checkpoint restore is not available")


def restore_suggestions(root: Path, checkpoint_id: str, cap: int = 5) -> dict[str, object]:
    engine = get_checkpoint_engine()
    if hasattr(engine, "restore_suggestions"):
        return engine.restore_suggestions(root, checkpoint_id, cap)  # type: ignore[attr-defined]
    raise RuntimeError("checkpoint restore suggestions are not available")


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
