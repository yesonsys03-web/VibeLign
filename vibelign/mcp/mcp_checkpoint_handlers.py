# === ANCHOR: MCP_CHECKPOINT_HANDLERS_START ===
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, cast


# === ANCHOR: MCP_CHECKPOINT_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_CHECKPOINT_HANDLERS___CALL___START ===
# === ANCHOR: MCP_CHECKPOINT_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_CHECKPOINT_HANDLERS___CALL___END ===


# === ANCHOR: MCP_CHECKPOINT_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_CHECKPOINT_HANDLERS__TEXT_END ===


def _json_text(factory: TextContentFactory, payload: dict[str, object]) -> list[object]:
    return _text(factory, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in cast(list[object], value) if str(item)]


# === ANCHOR: MCP_CHECKPOINT_HANDLERS_HANDLE_CHECKPOINT_CREATE_START ===
def handle_checkpoint_create(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_CHECKPOINT_HANDLERS_HANDLE_CHECKPOINT_CREATE_END ===
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import create_checkpoint, friendly_time

    message = str(arguments.get("message", ""))
    summary = create_checkpoint(root, message)
    if summary is None:
        text = "변경사항이 없어 체크포인트를 생성하지 않았습니다."
    else:
        text = (
            f"✓ 체크포인트 저장 완료\n"
            f"  ID: {summary.checkpoint_id}\n"
            f"  시간: {friendly_time(summary.created_at)}\n"
            f"  파일: {summary.file_count}개\n"
            f"  메시지: {summary.message}"
        )
    return _text(text_content, text)


def handle_checkpoint_diff(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import diff_checkpoints

    from_id = str(arguments.get("from_checkpoint_id", ""))
    to_id = str(arguments.get("to_checkpoint_id", ""))
    if not from_id or not to_id:
        return _json_text(
            text_content,
            {"ok": False, "error": "from_checkpoint_id and to_checkpoint_id are required"},
        )
    return _json_text(
        text_content,
        {"ok": True, "diff": diff_checkpoints(root, from_id, to_id)},
    )


def handle_checkpoint_preview_restore(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import preview_restore

    checkpoint_id = str(arguments.get("checkpoint_id", ""))
    if not checkpoint_id:
        return _json_text(text_content, {"ok": False, "error": "checkpoint_id is required"})
    relative_paths = _string_list(arguments.get("relative_paths"))
    preview = preview_restore(root, checkpoint_id, relative_paths or None)
    return _json_text(text_content, {"ok": True, "preview": preview})


def handle_checkpoint_restore_files(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import restore_files

    checkpoint_id = str(arguments.get("checkpoint_id", ""))
    relative_paths = _string_list(arguments.get("relative_paths"))
    if not checkpoint_id or not relative_paths:
        return _json_text(
            text_content,
            {"ok": False, "error": "checkpoint_id and relative_paths are required"},
        )
    restored_count = restore_files(root, checkpoint_id, relative_paths)
    return _json_text(text_content, {"ok": True, "restored_count": restored_count})


def handle_checkpoint_restore_suggestions(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import restore_suggestions

    checkpoint_id = str(arguments.get("checkpoint_id", ""))
    if not checkpoint_id:
        return _json_text(text_content, {"ok": False, "error": "checkpoint_id is required"})
    cap_value = arguments.get("cap", 5)
    cap = cap_value if isinstance(cap_value, int) else 5
    suggestions = restore_suggestions(root, checkpoint_id, cap)
    return _json_text(text_content, {"ok": True, **suggestions})


def handle_checkpoint_has_changes(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import has_changes_since_checkpoint

    checkpoint_id = str(arguments.get("checkpoint_id", ""))
    if not checkpoint_id:
        return _json_text(text_content, {"ok": False, "error": "checkpoint_id is required"})
    return _json_text(
        text_content,
        {"ok": True, "has_changes": has_changes_since_checkpoint(root, checkpoint_id)},
    )


def handle_retention_apply(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import apply_retention

    _ = arguments
    return _json_text(text_content, {"ok": True, "cleanup": apply_retention(root)})


# === ANCHOR: MCP_CHECKPOINT_HANDLERS_HANDLE_CHECKPOINT_LIST_START ===
def handle_checkpoint_list(
    root: Path, text_content: TextContentFactory
# === ANCHOR: MCP_CHECKPOINT_HANDLERS_HANDLE_CHECKPOINT_LIST_END ===
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import friendly_time, list_checkpoints

    checkpoints = list_checkpoints(root)
    if not checkpoints:
        return _text(text_content, "저장된 체크포인트가 없습니다.")
    lines = ["# 체크포인트 목록\n"]
    for checkpoint in checkpoints:
        pin = " [보호]" if checkpoint.pinned else ""
        lines.append(
            f"- `{checkpoint.checkpoint_id}`  "
            + f"{friendly_time(checkpoint.created_at)}  "
            + f"{checkpoint.message}{pin}"
        )
    return _text(text_content, "\n".join(lines))


# === ANCHOR: MCP_CHECKPOINT_HANDLERS_HANDLE_CHECKPOINT_RESTORE_START ===
def handle_checkpoint_restore(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_CHECKPOINT_HANDLERS_HANDLE_CHECKPOINT_RESTORE_END ===
) -> list[object]:
    from vibelign.core.checkpoint_engine.router import (
        get_last_restore_error,
        restore_checkpoint,
    )

    checkpoint_id = str(arguments.get("checkpoint_id", ""))
    if not checkpoint_id:
        return _text(text_content, "오류: checkpoint_id가 필요합니다.")
    ok = restore_checkpoint(root, checkpoint_id)
    text = (
        f"✓ `{checkpoint_id}` 시점으로 복원했습니다."
        if ok
        else f"오류: {get_last_restore_error()}"
    )
    return _text(text_content, text)
# === ANCHOR: MCP_CHECKPOINT_HANDLERS_END ===
