# === ANCHOR: CHECKPOINT_ENGINE_INIT_START ===
"""Checkpoint engine façade exports.

Module map: contracts.py defines Protocols; python_engine.py keeps the legacy
adapter; rust_engine.py is a thin compatibility wrapper over requests.py and
responses.py; rust_checkpoint_engine.py adapts Rust to the Protocol; router.py
selects the default engine; shadow_runner.py is opt-in parity tooling;
auto_backup.py handles post-commit backups.
"""

from vibelign.core.checkpoint_engine.contracts import (
    CheckpointEngine,
    CheckpointSummary,
    RetentionPolicy,
)
from vibelign.core.checkpoint_engine.rust_checkpoint_engine import RustCheckpointEngine
from vibelign.core.checkpoint_engine.router import (
    create_checkpoint,
    diff_checkpoints,
    friendly_time,
    get_checkpoint_engine,
    get_last_restore_error,
    has_changes_since_checkpoint,
    list_checkpoints,
    preview_restore,
    prune_checkpoints,
    restore_files,
    restore_checkpoint,
    restore_suggestions,
    apply_retention,
)

__all__ = [
    "CheckpointEngine",
    "CheckpointSummary",
    "RetentionPolicy",
    "RustCheckpointEngine",
    "create_checkpoint",
    "diff_checkpoints",
    "friendly_time",
    "get_checkpoint_engine",
    "get_last_restore_error",
    "has_changes_since_checkpoint",
    "list_checkpoints",
    "preview_restore",
    "prune_checkpoints",
    "restore_files",
    "restore_checkpoint",
    "restore_suggestions",
    "apply_retention",
]
# === ANCHOR: CHECKPOINT_ENGINE_INIT_END ===
