# === ANCHOR: CHECKPOINT_ENGINE_REQUESTS_START ===
from __future__ import annotations

from pathlib import Path


def checkpoint_create_request(
    root: Path,
    message: str,
    *,
    trigger: str | None = None,
    git_commit_sha: str | None = None,
    git_commit_message: str | None = None,
) -> dict[str, object]:
    request: dict[str, object] = {
        "command": "checkpoint_create",
        "root": str(root),
        "message": message,
    }
    if trigger is not None:
        request["trigger"] = trigger
    if git_commit_sha is not None:
        request["git_commit_sha"] = git_commit_sha
    if git_commit_message is not None:
        request["git_commit_message"] = git_commit_message
    return request


def checkpoint_list_request(root: Path) -> dict[str, object]:
    return {"command": "checkpoint_list", "root": str(root)}


def checkpoint_restore_request(root: Path, checkpoint_id: str) -> dict[str, object]:
    return {
        "command": "checkpoint_restore",
        "root": str(root),
        "checkpoint_id": checkpoint_id,
    }


def checkpoint_diff_request(
    root: Path, from_checkpoint_id: str, to_checkpoint_id: str
) -> dict[str, object]:
    return {
        "command": "checkpoint_diff",
        "root": str(root),
        "from_checkpoint_id": from_checkpoint_id,
        "to_checkpoint_id": to_checkpoint_id,
    }


def checkpoint_preview_request(
    root: Path, checkpoint_id: str, relative_paths: list[str] | None = None
) -> dict[str, object]:
    request: dict[str, object] = {
        "command": "checkpoint_restore_files_preview"
        if relative_paths is not None
        else "checkpoint_restore_preview",
        "root": str(root),
        "checkpoint_id": checkpoint_id,
    }
    if relative_paths is not None:
        request["relative_paths"] = relative_paths
    return request


def checkpoint_restore_files_request(
    root: Path, checkpoint_id: str, relative_paths: list[str]
) -> dict[str, object]:
    return {
        "command": "checkpoint_restore_files_safe",
        "root": str(root),
        "checkpoint_id": checkpoint_id,
        "relative_paths": relative_paths,
    }


def checkpoint_restore_suggestions_request(
    root: Path, checkpoint_id: str, cap: int = 5
) -> dict[str, object]:
    return {
        "command": "checkpoint_restore_suggestions",
        "root": str(root),
        "checkpoint_id": checkpoint_id,
        "cap": cap,
    }


def checkpoint_prune_request(root: Path, keep_latest: int) -> dict[str, object]:
    return {"command": "checkpoint_prune", "root": str(root), "keep_latest": keep_latest}


def retention_apply_request(root: Path) -> dict[str, object]:
    return {"command": "retention_apply", "root": str(root)}


def backup_db_viewer_inspect_request(root: Path) -> dict[str, object]:
    return {"command": "backup_db_viewer_inspect", "root": str(root)}


def backup_db_maintenance_request(root: Path, *, apply: bool = False) -> dict[str, object]:
    return {"command": "backup_db_maintenance", "root": str(root), "apply": apply}


# === ANCHOR: CHECKPOINT_ENGINE_REQUESTS_END ===
