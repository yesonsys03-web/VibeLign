# === ANCHOR: MCP_PATCH_HANDLERS_START ===
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.meta_paths import MetaPaths
from vibelign.mcp.mcp_state_store import (
    load_patch_session,
    new_patch_session_id,
    patch_session_now,
    save_patch_session,
)


# === ANCHOR: MCP_PATCH_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_PATCH_HANDLERS___CALL___START ===
# === ANCHOR: MCP_PATCH_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_PATCH_HANDLERS___CALL___END ===


# === ANCHOR: MCP_PATCH_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_PATCH_HANDLERS__TEXT_END ===


# === ANCHOR: MCP_PATCH_HANDLERS_HANDLE_PATCH_GET_START ===
def handle_patch_get(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_PATCH_HANDLERS_HANDLE_PATCH_GET_END ===
) -> list[object]:
    from vibelign.patch.patch_builder import build_patch_data

    request = str(arguments.get("request", ""))
    if not request:
        return _text(
            text_content,
            json.dumps(
                {"ok": False, "error": "request가 필요합니다.", "data": None},
                indent=2,
                ensure_ascii=False,
            ),
        )
    lazy_fanout = bool(arguments.get("lazy_fanout"))
    meta = MetaPaths(root)
    active_session = load_patch_session(meta)
    verification_blocked = bool(
        active_session and active_session.get("needs_verification")
    )
    data = build_patch_data(root, request, lazy_fanout=lazy_fanout)
    patch_plan = cast(dict[str, object], data["patch_plan"])
    contract = cast(dict[str, object], data["contract"])
    scope = cast(dict[str, object], contract.get("scope", {}))
    session = active_session if isinstance(active_session, dict) else None
    step_list = cast(list[object], patch_plan.get("steps") or [])
    sub_intents = [
        str(item)
        for item in cast(list[object], patch_plan.get("sub_intents") or [])
        if str(item).strip()
    ]
    pending_sub_intents = [
        str(item)
        for item in cast(list[object], patch_plan.get("pending_sub_intents") or [])
        if str(item).strip()
    ]
    if not verification_blocked and (len(step_list) > 1 or pending_sub_intents):
        session = {
            "session_id": str(
                (active_session or {}).get("session_id") or new_patch_session_id()
            ),
            "request": request,
            "target_file": patch_plan["target_file"],
            "target_anchor": patch_plan["target_anchor"],
            "sub_intents": sub_intents,
            "pending_sub_intents": pending_sub_intents,
            "step_count": len(step_list),
            "needs_verification": False,
            "active": True,
            "updated_at": patch_session_now(),
        }
        save_patch_session(meta, session)
    result: dict[str, object] = {
        "schema_version": patch_plan["schema_version"],
        "target_file": patch_plan["target_file"],
        "target_anchor": patch_plan["target_anchor"],
        "steps": patch_plan.get("steps"),
        "sub_intents": patch_plan.get("sub_intents"),
        "pending_sub_intents": patch_plan.get("pending_sub_intents"),
        "strict_patch": data.get("strict_patch"),
        "destination_target_file": scope.get("destination_target_file"),
        "destination_target_anchor": scope.get("destination_target_anchor"),
        "codespeak": patch_plan["codespeak"],
        "interpretation": patch_plan["interpretation"],
        "confidence": patch_plan["confidence"],
        "constraints": patch_plan["constraints"],
        "allowed_ops": contract["allowed_ops"],
        "status": contract["status"],
        "clarifying_questions": contract["clarifying_questions"],
        "move_summary": contract.get("move_summary"),
        "rationale": patch_plan["rationale"],
    }
    if verification_blocked:
        result["session"] = active_session
        result["status"] = "NEEDS_CLARIFICATION"
        questions = cast(list[object], result.get("clarifying_questions") or [])
        normalized_questions = [str(item) for item in questions if str(item).strip()]
        blocked_question = (
            "이전 패치를 적용한 뒤 아직 guard_check로 검증하지 않았어요. "
            "다음 단계로 가기 전에 guard_check를 먼저 실행해 주세요."
        )
        if blocked_question not in normalized_questions:
            normalized_questions.append(blocked_question)
        result["clarifying_questions"] = normalized_questions
        result["session_blocked"] = True
    elif session is not None:
        result["session"] = session
    return _text(text_content, json.dumps(result, indent=2, ensure_ascii=False))


# === ANCHOR: MCP_PATCH_HANDLERS_HANDLE_PATCH_APPLY_START ===
def handle_patch_apply(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_PATCH_HANDLERS_HANDLE_PATCH_APPLY_END ===
) -> list[object]:
    from vibelign.core.strict_patch import apply_strict_patch

    raw_patch = arguments.get("strict_patch")
    if isinstance(raw_patch, str):
        try:
            strict_patch = cast(dict[str, object], json.loads(raw_patch))
        except json.JSONDecodeError:
            strict_patch = None
    elif isinstance(raw_patch, dict):
        strict_patch = cast(dict[str, object], raw_patch)
    else:
        strict_patch = None
    if strict_patch is None:
        return _text(
            text_content,
            json.dumps(
                {"ok": False, "error": "strict_patch JSON object가 필요합니다."},
                indent=2,
                ensure_ascii=False,
            ),
        )
    result = apply_strict_patch(
        root,
        strict_patch,
        dry_run=bool(arguments.get("dry_run")),
    )
    meta = MetaPaths(root)
    session = load_patch_session(meta)
    if (
        session is not None
        and bool(result.get("ok"))
        and not bool(result.get("dry_run"))
    ):
        session["needs_verification"] = True
        session["verified_at"] = None
        session["last_applied_at"] = patch_session_now()
        session["applied_operation_count"] = result.get("applied_operation_count")
        session["active"] = True
        save_patch_session(meta, session)
        result["session"] = session
    return _text(text_content, json.dumps(result, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_PATCH_HANDLERS_END ===
