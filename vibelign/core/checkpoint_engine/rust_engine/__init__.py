# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_START ===
from __future__ import annotations

import os
from pathlib import Path

from vibelign.core.local_checkpoints import CheckpointSummary
from vibelign.core.checkpoint_engine.requests import (
    backup_db_maintenance_request,
    backup_db_viewer_inspect_request,
    backup_graph_summary_request,
    checkpoint_create_request,
    checkpoint_diff_request,
    checkpoint_list_request,
    checkpoint_preview_request,
    checkpoint_prune_request,
    checkpoint_restore_files_request,
    checkpoint_restore_request,
    checkpoint_restore_suggestions_request,
    retention_apply_request,
)
from vibelign.core.checkpoint_engine.responses import (
    parse_backup_db_maintenance,
    parse_backup_db_viewer_inspect,
    parse_backup_graph_summary,
    parse_checkpoint_create,
    parse_checkpoint_list,
    parse_diff,
    parse_preview,
    parse_prune,
    parse_restore,
    parse_restore_files,
    parse_retention,
    parse_suggestions,
)
from vibelign.core.checkpoint_engine.rust_engine.discovery import (
    RustEngineAvailability,
    _binary_name,
    _candidate_paths,
    _sha256,
    _verify_integrity,
    find_rust_engine,
)
from vibelign.core.checkpoint_engine.rust_engine.daemon_client import (
    call_rust_engine_daemon,
    healthcheck_rust_engine_daemon,
    is_rust_engine_daemon_running,
    shutdown_rust_engine_daemon,
)
from vibelign.core.checkpoint_engine.rust_engine.transport_oneshot import (
    RustEngineResult,
    call_rust_engine,
)

_BACKUP_COMMAND_TIMEOUT_SECONDS = 90
_DAEMON_FALLBACK_CODES = {
    "RUST_ENGINE_DAEMON_UNAVAILABLE",
    "RUST_ENGINE_DAEMON_UNSUPPORTED",
}


def _daemon_enabled() -> bool:
    return os.environ.get("VIBELIGN_ENGINE_DAEMON", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _call_rust_engine_transport(
    root: Path, request: dict[str, object], timeout_seconds: int = 30
) -> RustEngineResult:
    if not _daemon_enabled():
        return call_rust_engine(root, request, timeout_seconds=timeout_seconds)
    daemon_result = call_rust_engine_daemon(
        root, request, timeout_seconds=timeout_seconds, start_if_missing=True
    )
    if daemon_result.ok or daemon_result.error_code not in _DAEMON_FALLBACK_CODES:
        return daemon_result
    return call_rust_engine(root, request, timeout_seconds=timeout_seconds)


def create_checkpoint_with_rust(
    root: Path,
    message: str,
    *,
    trigger: str | None = None,
    git_commit_sha: str | None = None,
    git_commit_message: str | None = None,
) -> tuple[CheckpointSummary | None, str | None]:
    request = checkpoint_create_request(
        root,
        message,
        trigger=trigger,
        git_commit_sha=git_commit_sha,
        git_commit_message=git_commit_message,
    )
    result = _call_rust_engine_transport(
        root, request, timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS
    )
    return parse_checkpoint_create(result, message)


def list_checkpoints_with_rust(root: Path) -> tuple[list[CheckpointSummary] | None, str | None]:
    result = _call_rust_engine_transport(root, checkpoint_list_request(root))
    return parse_checkpoint_list(result)


def restore_checkpoint_with_rust(root: Path, checkpoint_id: str) -> tuple[bool, str | None]:
    result = _call_rust_engine_transport(
        root,
        checkpoint_restore_request(root, checkpoint_id),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_restore(result)


def diff_checkpoints_with_rust(
    root: Path, from_checkpoint_id: str, to_checkpoint_id: str
) -> tuple[dict[str, object] | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        checkpoint_diff_request(root, from_checkpoint_id, to_checkpoint_id),
    )
    return parse_diff(result)


def preview_restore_with_rust(
    root: Path, checkpoint_id: str, relative_paths: list[str] | None = None
) -> tuple[dict[str, object] | None, str | None]:
    request = checkpoint_preview_request(root, checkpoint_id, relative_paths)
    result = _call_rust_engine_transport(
        root, request, timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS
    )
    return parse_preview(result)


def restore_files_with_rust(
    root: Path, checkpoint_id: str, relative_paths: list[str]
) -> tuple[int | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        checkpoint_restore_files_request(root, checkpoint_id, relative_paths),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_restore_files(result)


def restore_suggestions_with_rust(
    root: Path, checkpoint_id: str, cap: int = 5
) -> tuple[dict[str, object] | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        checkpoint_restore_suggestions_request(root, checkpoint_id, cap),
    )
    return parse_suggestions(result)


def prune_checkpoints_with_rust(
    root: Path, keep_latest: int = 30
) -> tuple[dict[str, int] | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        checkpoint_prune_request(root, keep_latest),
    )
    return parse_prune(result)


def apply_retention_with_rust(root: Path) -> tuple[dict[str, object] | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        retention_apply_request(root),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_retention(result)


def inspect_backup_db_with_rust(root: Path) -> tuple[dict[str, object] | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        backup_db_viewer_inspect_request(root),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_backup_db_viewer_inspect(result)


def maintain_backup_db_with_rust(
    root: Path, *, apply: bool = False
) -> tuple[dict[str, object] | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        backup_db_maintenance_request(root, apply=apply),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_backup_db_maintenance(result)


def backup_graph_summary_with_rust(root: Path) -> tuple[dict[str, object] | None, str | None]:
    result = _call_rust_engine_transport(
        root,
        backup_graph_summary_request(root),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_backup_graph_summary(result)


# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_END ===

__all__ = [
    "RustEngineAvailability",
    "RustEngineResult",
    "_binary_name",
    "_candidate_paths",
    "_sha256",
    "_verify_integrity",
    "find_rust_engine",
    "call_rust_engine",
    "call_rust_engine_daemon",
    "healthcheck_rust_engine_daemon",
    "is_rust_engine_daemon_running",
    "shutdown_rust_engine_daemon",
    "create_checkpoint_with_rust",
    "list_checkpoints_with_rust",
    "restore_checkpoint_with_rust",
    "diff_checkpoints_with_rust",
    "preview_restore_with_rust",
    "restore_files_with_rust",
    "restore_suggestions_with_rust",
    "prune_checkpoints_with_rust",
    "apply_retention_with_rust",
    "inspect_backup_db_with_rust",
    "maintain_backup_db_with_rust",
    "backup_graph_summary_with_rust",
]
