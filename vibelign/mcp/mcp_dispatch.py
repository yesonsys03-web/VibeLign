# === ANCHOR: MCP_DISPATCH_START ===
from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from vibelign.mcp.mcp_handler_registry import DISPATCH_TABLE
from vibelign.mcp.mcp_handler_registry import TextContentFactory
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import (
    add_relevant_file,
    add_verification,
    record_checkpoint,
)


# === ANCHOR: MCP_DISPATCH_DISPATCHCALLABLE_START ===
class DispatchCallable(Protocol):
    # === ANCHOR: MCP_DISPATCH___CALL___START ===
    def __call__(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_DISPATCH_DISPATCHCALLABLE_END ===
    # === ANCHOR: MCP_DISPATCH___CALL___END ===
    ) -> list[object]: ...


# === ANCHOR: MCP_DISPATCH__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_DISPATCH__TEXT_END ===


# === ANCHOR: MCP_DISPATCH_CALL_TOOL_DISPATCH_START ===
async def call_tool_dispatch(
    name: str,
    arguments: dict[str, object],
    *,
    root: Path,
    text_content: TextContentFactory,
# === ANCHOR: MCP_DISPATCH_CALL_TOOL_DISPATCH_END ===
) -> list[object]:
    handler = cast(DispatchCallable | None, DISPATCH_TABLE.get(name))
    if handler is None:
        return _text(text_content, f"알 수 없는 도구: {name}")
    result = handler(root, arguments, text_content)
    try:
        _auto_capture_narrative(name, arguments, result, root)
    except Exception:
        pass  # narrative 캡처 실패는 도구 결과를 망치지 않는다.
    return result


def _auto_capture_narrative(
    name: str,
    arguments: dict[str, object],
    result: list[object],
    root: Path,
) -> None:
    """주요 도구 호출 후 work_memory 자동 누적 (decisions[] 는 절대 안 건드림)."""
    wm = MetaPaths(root).work_memory_path

    if name == "guard_check":
        text = _flatten_result_text(result)
        if text:
            add_verification(wm, f"guard_check -> {text[:200]}")

    elif name == "checkpoint_create":
        msg = arguments.get("message")
        if isinstance(msg, str) and msg.strip():
            # checkpoint 는 사실(state save) 이므로 recent_events 에만.
            record_checkpoint(wm, msg)

    elif name == "patch_apply":
        strict = arguments.get("strict_patch")
        if not isinstance(strict, dict):
            return
        if arguments.get("dry_run") is True or strict.get("dry_run") is True:
            return
        target = strict.get("target")
        if isinstance(target, dict):
            file_path = target.get("file")
            if isinstance(file_path, str) and file_path:
                anchor = target.get("anchor", "")
                why = (
                    f"patch_apply target (anchor: {anchor})"
                    if isinstance(anchor, str) and anchor
                    else "patch_apply target"
                )
                add_relevant_file(wm, file_path, why)


def _flatten_result_text(result: list[object]) -> str:
    parts: list[str] = []
    for item in result:
        if isinstance(item, dict):
            text = item.get("text")
        else:
            text = getattr(item, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return " | ".join(parts)
# === ANCHOR: MCP_DISPATCH_END ===
