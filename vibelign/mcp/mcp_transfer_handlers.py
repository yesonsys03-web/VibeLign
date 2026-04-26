# === ANCHOR: MCP_TRANSFER_HANDLERS_START ===
from __future__ import annotations

from datetime import datetime as _dt
from pathlib import Path
from typing import Protocol, cast


# === ANCHOR: MCP_TRANSFER_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_TRANSFER_HANDLERS___CALL___START ===
# === ANCHOR: MCP_TRANSFER_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_TRANSFER_HANDLERS___CALL___END ===


# === ANCHOR: MCP_TRANSFER_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_TRANSFER_HANDLERS__TEXT_END ===


# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_HANDOFF_CREATE_START ===
def handle_handoff_create(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_HANDOFF_CREATE_END ===
) -> list[object]:
    from vibelign.commands.vib_transfer_cmd import (
        HandoffData,
        build_context_content,
        enrich_handoff_with_work_memory,
        get_changed_files,
        get_recent_checkpoints,
        inject_agents_handoff_instruction,
    )

    session_summary = str(arguments.get("session_summary", ""))
    first_next_action = str(arguments.get("first_next_action", ""))
    completed_work = arguments.get("completed_work")
    unfinished_work = arguments.get("unfinished_work")
    raw_dc = arguments.get("decision_context")
    notes = arguments.get("notes")

    if not session_summary or not first_next_action:
        return _text(
            text_content,
            "오류: session_summary와 first_next_action은 필수 항목입니다.",
        )

    checkpoints = get_recent_checkpoints(root, n=1)
    latest_cp = checkpoints[0]["message"] if checkpoints else None

    full_summary = session_summary
    if notes:
        full_summary = f"{session_summary} | {notes}"

    decision_context = None
    if isinstance(raw_dc, dict):
        decision_context_raw = cast(dict[str, object], raw_dc)
        decision_context = {
            "tried": str(decision_context_raw.get("tried", "") or "(not provided)"),
            "blocked_by": str(
                decision_context_raw.get("blocked_by", "") or "(not provided)"
            ),
            "switched_to": str(
                decision_context_raw.get("switched_to", "") or "(not provided)"
            ),
        }

    handoff_data = cast(
        HandoffData,
        cast(
            object,
            {
                "generated_at": _dt.now().strftime("%Y-%m-%d %H:%M"),
                "source": "mcp_provided",
                "quality": "ai-drafted",
                "session_summary": full_summary,
                "changed_files": get_changed_files(root),
                "completed_work": str(completed_work) if completed_work else None,
                "unfinished_work": str(unfinished_work) if unfinished_work else None,
                "first_next_action": first_next_action,
                "decision_context": decision_context,
                "latest_checkpoint": latest_cp,
            },
        ),
    )

    handoff_data = enrich_handoff_with_work_memory(root, handoff_data)

    content = build_context_content(root, handoff_data=handoff_data)
    ctx_path = root / "PROJECT_CONTEXT.md"
    _ = ctx_path.write_text(content, encoding="utf-8")
    inject_agents_handoff_instruction(root)
    return _text(
        text_content,
        "✓ Session Handoff 블록 생성 완료\n"
        + f"  파일: {ctx_path}\n"
        + "  새 AI에게 PROJECT_CONTEXT.md 상단의 Session Handoff 블록을 읽혀주세요.",
    )


# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_PROJECT_CONTEXT_GET_START ===
def handle_project_context_get(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_PROJECT_CONTEXT_GET_END ===
) -> list[object]:
    from vibelign.commands.vib_transfer_cmd import build_context_content

    compact = bool(arguments.get("compact", False))
    full = bool(arguments.get("full", False))
    ctx_path = root / "PROJECT_CONTEXT.md"

    if ctx_path.exists() and not compact and not full:
        content = ctx_path.read_text(encoding="utf-8")
    else:
        content = build_context_content(root, compact=compact, full=full)

    return _text(text_content, content)
# === ANCHOR: MCP_TRANSFER_HANDLERS_END ===
