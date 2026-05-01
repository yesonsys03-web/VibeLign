# === ANCHOR: CHECKPOINT_ENGINE_RESPONSES_START ===
from __future__ import annotations

from typing import Protocol, cast

from vibelign.core.local_checkpoints import CheckpointFileSummary, CheckpointSummary


class RustResultLike(Protocol):
    ok: bool
    payload: dict[str, object]
    error_code: str | None
    error_message: str | None


def parse_checkpoint_create(
    result: RustResultLike, fallback_message: str
) -> tuple[CheckpointSummary | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust checkpoint failed")
    result_kind = result.payload.get("result")
    if result_kind == "no_changes":
        return None, None
    if result_kind != "created":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected checkpoint create result"
    summary = summary_from_payload(result.payload, fallback_message=fallback_message)
    if summary is None:
        return None, "RUST_ENGINE_PROTOCOL_ERROR: created response missing checkpoint_id"
    return summary, None


def parse_checkpoint_list(
    result: RustResultLike,
) -> tuple[list[CheckpointSummary] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust checkpoint list failed")
    raw_checkpoints = result.payload.get("checkpoints")
    if not isinstance(raw_checkpoints, list):
        return None, "RUST_ENGINE_PROTOCOL_ERROR: list response missing checkpoints"
    summaries: list[CheckpointSummary] = []
    for raw_item in cast(list[object], raw_checkpoints):
        if isinstance(raw_item, dict):
            summary = summary_from_payload(cast(dict[str, object], raw_item))
            if summary is not None:
                summaries.append(summary)
    return summaries, None


def parse_restore(result: RustResultLike) -> tuple[bool, str | None]:
    if not result.ok:
        return False, format_error(result, "rust checkpoint restore failed")
    return True, None


def parse_diff(result: RustResultLike) -> tuple[dict[str, object] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust checkpoint diff failed")
    if result.payload.get("result") != "diffed":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected checkpoint diff result"
    diff = result.payload.get("diff")
    if not isinstance(diff, dict):
        return None, "RUST_ENGINE_PROTOCOL_ERROR: diff response missing diff"
    return cast(dict[str, object], diff), None


def parse_preview(result: RustResultLike) -> tuple[dict[str, object] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust checkpoint preview failed")
    if result.payload.get("result") != "previewed":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected checkpoint preview result"
    preview = result.payload.get("preview")
    if not isinstance(preview, dict):
        return None, "RUST_ENGINE_PROTOCOL_ERROR: preview response missing preview"
    return cast(dict[str, object], preview), None


def parse_restore_files(result: RustResultLike) -> tuple[int | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust checkpoint selected restore failed")
    if result.payload.get("result") != "restored_files":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected selected restore result"
    return coerce_int(result.payload.get("restored_count", 0)), None


def parse_suggestions(
    result: RustResultLike,
) -> tuple[dict[str, object] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust checkpoint suggestions failed")
    if result.payload.get("result") != "suggested":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected checkpoint suggestions result"
    suggestions = result.payload.get("suggestions")
    if not isinstance(suggestions, list):
        return None, "RUST_ENGINE_PROTOCOL_ERROR: suggestions response missing suggestions"
    return {"suggestions": suggestions, "legacy_notice": result.payload.get("legacy_notice")}, None


def parse_prune(result: RustResultLike) -> tuple[dict[str, int] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust checkpoint prune failed")
    if "pruned_count" not in result.payload or "pruned_bytes" not in result.payload:
        return None, "RUST_ENGINE_PROTOCOL_ERROR: prune response missing counts"
    return {
        "count": coerce_int(result.payload.get("pruned_count", 0)),
        "bytes": coerce_int(result.payload.get("pruned_bytes", 0)),
    }, None


def parse_retention(result: RustResultLike) -> tuple[dict[str, object] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust retention cleanup failed")
    if result.payload.get("result") != "retention_applied":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected retention cleanup result"
    return {
        "count": coerce_int(result.payload.get("pruned_count", 0)),
        "planned_count": coerce_int(result.payload.get("planned_count", 0)),
        "planned_bytes": coerce_int(result.payload.get("planned_bytes", 0)),
        "reclaimed_bytes": coerce_int(result.payload.get("reclaimed_bytes", 0)),
        "partial_failure": bool(result.payload.get("partial_failure", False)),
    }, None


def parse_backup_db_viewer_inspect(
    result: RustResultLike,
) -> tuple[dict[str, object] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust backup db viewer inspect failed")
    if result.payload.get("result") != "backup_db_viewer_inspect":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected backup_db_viewer_inspect result"
    return dict(result.payload), None


def parse_backup_db_maintenance(
    result: RustResultLike,
) -> tuple[dict[str, object] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust backup db maintenance failed")
    if result.payload.get("result") != "backup_db_maintenance":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected backup_db_maintenance result"
    return dict(result.payload), None


def summary_from_payload(
    payload: dict[str, object], fallback_message: str = ""
) -> CheckpointSummary | None:
    checkpoint_id = payload.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        return None
    trigger = payload.get("trigger")
    git_commit_message = payload.get("git_commit_message")
    files = payload.get("files")
    return CheckpointSummary(
        checkpoint_id=checkpoint_id,
        created_at=str(payload.get("created_at", checkpoint_id)),
        message=str(payload.get("message", fallback_message)),
        file_count=coerce_int(payload.get("file_count", 0)),
        total_size_bytes=coerce_int(payload.get("total_size_bytes", 0)),
        pinned=bool(payload.get("pinned", False)),
        trigger=trigger if isinstance(trigger, str) else None,
        git_commit_message=git_commit_message if isinstance(git_commit_message, str) else None,
        files=parse_file_summaries(files),
    )


def parse_file_summaries(value: object) -> list[CheckpointFileSummary]:
    if not isinstance(value, list):
        return []
    summaries: list[CheckpointFileSummary] = []
    for raw in cast(list[object], value):
        if not isinstance(raw, dict):
            continue
        item = cast(dict[str, object], raw)
        path = item.get("relative_path") or item.get("path")
        if not isinstance(path, str) or not path:
            continue
        summaries.append(
            CheckpointFileSummary(
                path=path.replace("\\", "/"),
                size_bytes=coerce_int(item.get("size", item.get("size_bytes", 0))),
            )
        )
    return summaries


def coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def format_error(result: RustResultLike, fallback: str) -> str:
    code = result.error_code or "RUST_ENGINE_ERROR"
    message = result.error_message or fallback
    return f"{code}: {message}"


# === ANCHOR: CHECKPOINT_ENGINE_RESPONSES_END ===
