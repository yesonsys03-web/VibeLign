# === ANCHOR: MCP_SERVER_START ===
"""VibeLign MCP Server — stdio transport.

사용법:
    vibelign-mcp          # 설치 후 직접 실행
    python -m vibelign.mcp_server

Claude Code .claude/settings.json 등록:
    {
      "mcpServers": {
        "vibelign": {
          "command": "vibelign-mcp",
          "args": []
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root


app = Server("vibelign")


def _root() -> Path:
    return resolve_project_root(Path.cwd())


_PATCH_SESSION_KEY = "patch_session"


def _load_state(meta: MetaPaths) -> dict[str, object]:
    if not meta.state_path.exists():
        return {}
    try:
        raw_state = json.loads(meta.state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    if not isinstance(raw_state, dict):
        return {}
    return {
        str(key): value for key, value in cast(dict[object, object], raw_state).items()
    }


def _save_state(meta: MetaPaths, state: dict[str, object]) -> None:
    meta.ensure_vibelign_dirs()
    meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _load_patch_session(meta: MetaPaths) -> dict[str, object] | None:
    state = _load_state(meta)
    session = state.get(_PATCH_SESSION_KEY)
    if not isinstance(session, dict):
        return None
    return {
        str(key): value for key, value in cast(dict[object, object], session).items()
    }


def _save_patch_session(meta: MetaPaths, session: dict[str, object] | None) -> None:
    state = _load_state(meta)
    if session is None:
        state.pop(_PATCH_SESSION_KEY, None)
    else:
        state[_PATCH_SESSION_KEY] = session
    _save_state(meta, state)


def _patch_session_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_patch_session_id() -> str:
    return uuid.uuid4().hex


# === ANCHOR: MCP_SERVER_LIST_TOOLS_START ===
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # ── 체크포인트 ──────────────────────────────────────────────────────
        types.Tool(
            name="checkpoint_create",
            description="현재 프로젝트 상태를 체크포인트로 저장합니다. 작업 전 반드시 호출하세요.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "체크포인트 설명 (예: '로그인 완성')",
                    }
                },
                "required": ["message"],
            },
        ),
        types.Tool(
            name="checkpoint_list",
            description="저장된 체크포인트 목록을 반환합니다.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="checkpoint_restore",
            description="특정 체크포인트로 프로젝트를 복원합니다. checkpoint_list로 ID를 확인 후 사용하세요.",
            inputSchema={
                "type": "object",
                "properties": {
                    "checkpoint_id": {
                        "type": "string",
                        "description": "복원할 체크포인트 ID",
                    }
                },
                "required": ["checkpoint_id"],
            },
        ),
        # ── AI 컨텍스트 ─────────────────────────────────────────────────────
        types.Tool(
            name="project_context_get",
            description=(
                "현재 프로젝트의 요약 컨텍스트를 생성합니다. "
                "토큰이 부족하거나 AI 툴을 바꿀 때 이 내용을 새 AI에게 전달하면 "
                "어떤 프로젝트인지, 어떤 작업을 하고 있었는지 즉시 파악할 수 있습니다. "
                "토큰 절약에도 효과적입니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "compact": {
                        "type": "boolean",
                        "description": "간략 모드 — 파일 트리 깊이 2 (기본값: false)",
                    },
                    "full": {
                        "type": "boolean",
                        "description": "전체 모드 — 파일 트리 깊이 4 (기본값: false)",
                    },
                },
            },
        ),
        # ── 프로젝트 분석 ───────────────────────────────────────────────────
        types.Tool(
            name="doctor_run",
            description="프로젝트 건강 진단을 실행합니다. 점수, 상태, 권장 조치를 JSON으로 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "strict": {
                        "type": "boolean",
                        "description": "엄격 모드 (기본값: false)",
                    }
                },
            },
        ),
        types.Tool(
            name="guard_check",
            description="프로젝트 상태와 최근 변경사항을 분석하여 안전 여부를 판단합니다. pass/warn/fail 반환.",
            inputSchema={
                "type": "object",
                "properties": {
                    "strict": {
                        "type": "boolean",
                        "description": "엄격 모드 — warn도 fail로 처리 (기본값: false)",
                    },
                    "since_minutes": {
                        "type": "integer",
                        "description": "최근 N분 이내 변경사항 분석 (기본값: 30)",
                    },
                },
            },
        ),
        # ── 보호/가드 ────────────────────────────────────────────────────────
        types.Tool(
            name="protect_add",
            description="파일을 보호 목록에 추가합니다. AI가 수정하면 안 되는 파일을 등록하세요.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "보호할 파일의 상대 경로 목록",
                    }
                },
                "required": ["file_paths"],
            },
        ),
        # ── 패치 ─────────────────────────────────────────────────────────────
        types.Tool(
            name="patch_get",
            description=(
                "사용자의 자연어 요청을 CodeSpeak(구조화된 수정 지시어)로 번역하고, "
                "프로젝트 앵커 인덱스를 검색하여 수정할 파일과 정확한 위치(target_anchor)를 특정합니다. "
                "코드를 수정하기 전에 반드시 이 도구를 먼저 호출하고, "
                "반환된 target_file과 target_anchor 범위 안에서만 수정하세요."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "수정 요청 (예: '로그인 버튼 크기 키워줘')",
                    },
                    "lazy_fanout": {
                        "type": "boolean",
                        "description": (
                            "다중 의도가 있을 때 첫 의도만 상세 계획하고 "
                            "나머지는 pending_sub_intents로 돌려 비용을 줄임"
                        ),
                    },
                },
                "required": ["request"],
            },
        ),
        types.Tool(
            name="patch_apply",
            description=(
                "Strict Patch JSON을 validator 규칙으로 검증한 뒤 정확히 한 번 매치될 때만 적용합니다. "
                "적용 직전에 자동 checkpoint를 생성합니다. "
                "dry_run=true이면 검증만 하고 파일을 쓰지 않으며 checkpoint도 만들지 않습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "strict_patch": {
                        "type": "object",
                        "description": "patch_get 또는 handoff prompt에서 얻은 Strict Patch JSON",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "true면 검증만 수행 (워크스페이스 변경·checkpoint 없음)",
                    },
                },
                "required": ["strict_patch"],
            },
        ),
        # ── 핸드오프 ─────────────────────────────────────────────────────────
        types.Tool(
            name="handoff_create",
            description=(
                "현재 AI 세션 요약을 받아 PROJECT_CONTEXT.md 상단에 Session Handoff 블록을 생성합니다. "
                "토큰 한도 도달 또는 AI 툴 전환 직전에 호출하세요. "
                "새 AI가 이 블록을 읽으면 즉시 작업을 이어갈 수 있습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_summary": {
                        "type": "string",
                        "description": "오늘 한 작업 요약 (한두 줄 bullet)",
                    },
                    "first_next_action": {
                        "type": "string",
                        "description": "다음 AI가 가장 먼저 해야 할 일 (한 줄)",
                    },
                    "completed_work": {
                        "type": "string",
                        "description": "완료된 작업 요약 (선택)",
                    },
                    "unfinished_work": {
                        "type": "string",
                        "description": "미완료 작업 요약 (선택)",
                    },
                    "decision_context": {
                        "type": "object",
                        "description": "방향 전환 컨텍스트 (선택)",
                        "properties": {
                            "tried": {"type": "string"},
                            "blocked_by": {"type": "string"},
                            "switched_to": {"type": "string"},
                        },
                    },
                    "notes": {
                        "type": "string",
                        "description": "추가 메모나 블로커 (선택)",
                    },
                },
                "required": ["session_summary", "first_next_action"],
            },
        ),
        # ── 기타 ─────────────────────────────────────────────────────────────
        types.Tool(
            name="anchor_run",
            description=(
                "앵커가 없는 파일에 앵커를 자동으로 삽입합니다. "
                "코드 수정 작업 전 반드시 호출하세요. "
                "앵커가 있어야 AI가 정확한 위치를 찾아 수정할 수 있습니다."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="anchor_list",
            description="프로젝트의 앵커 인덱스를 반환합니다. vib scan을 먼저 실행해야 합니다.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="explain_get",
            description="최근 변경된 파일과 변경 내용을 분석하여 반환합니다. 작업 후 무엇이 바뀌었는지 확인할 때 사용하세요.",
            inputSchema={
                "type": "object",
                "properties": {
                    "since_minutes": {
                        "type": "integer",
                        "description": "최근 N분 이내 변경사항 분석 (기본값: 120)",
                    }
                },
            },
        ),
        types.Tool(
            name="config_get",
            description="VibeLign 현재 설정을 반환합니다.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── Action Engine ───────────────────────────────────────────────────
        types.Tool(
            name="doctor_plan",
            description="프로젝트 분석 결과를 실행 가능한 단계 목록(Plan)으로 반환합니다. 파일 수정 없음.",
            inputSchema={
                "type": "object",
                "properties": {
                    "strict": {
                        "type": "boolean",
                        "description": "엄격 모드 (기본값: false)",
                    }
                },
            },
        ),
        types.Tool(
            name="doctor_patch",
            description="Plan의 각 Action에 대한 변경 예정 미리보기를 반환합니다. 파일 수정 없음.",
            inputSchema={
                "type": "object",
                "properties": {
                    "strict": {
                        "type": "boolean",
                        "description": "엄격 모드 (기본값: false)",
                    }
                },
            },
        ),
        types.Tool(
            name="doctor_apply",
            description="Plan을 실행합니다. checkpoint 자동 생성 후 add_anchor 등 안전한 action만 적용.",
            inputSchema={
                "type": "object",
                "properties": {
                    "strict": {
                        "type": "boolean",
                        "description": "엄격 모드 (기본값: false)",
                    }
                },
            },
        ),
    ]


# === ANCHOR: MCP_SERVER_LIST_TOOLS_END ===


# === ANCHOR: MCP_SERVER_CALL_TOOL_START ===
@app.call_tool()
async def call_tool(name: str, arguments: dict[str, object]) -> list[types.TextContent]:
    root = _root()

    # ── checkpoint_create ──────────────────────────────────────────────────
    if name == "checkpoint_create":
        from vibelign.core.local_checkpoints import create_checkpoint, friendly_time

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
        return [types.TextContent(type="text", text=text)]

    # ── checkpoint_list ────────────────────────────────────────────────────
    if name == "checkpoint_list":
        from vibelign.core.local_checkpoints import list_checkpoints, friendly_time

        checkpoints = list_checkpoints(root)
        if not checkpoints:
            return [
                types.TextContent(type="text", text="저장된 체크포인트가 없습니다.")
            ]
        lines = ["# 체크포인트 목록\n"]
        for cp in checkpoints:
            pin = " [보호]" if cp.pinned else ""
            lines.append(
                f"- `{cp.checkpoint_id}`  "
                f"{friendly_time(cp.created_at)}  "
                f"{cp.message}{pin}"
            )
        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── checkpoint_restore ─────────────────────────────────────────────────
    if name == "checkpoint_restore":
        from vibelign.core.local_checkpoints import (
            get_last_restore_error,
            restore_checkpoint,
        )

        checkpoint_id = str(arguments.get("checkpoint_id", ""))
        if not checkpoint_id:
            return [
                types.TextContent(type="text", text="오류: checkpoint_id가 필요합니다.")
            ]
        ok = restore_checkpoint(root, checkpoint_id)
        if ok:
            text = f"✓ `{checkpoint_id}` 시점으로 복원했습니다."
        else:
            text = f"오류: {get_last_restore_error()}"
        return [types.TextContent(type="text", text=text)]

    # ── handoff_create ─────────────────────────────────────────────────────
    if name == "handoff_create":
        from vibelign.commands.vib_transfer_cmd import (
            HandoffData,
            _build_context_content,
            _get_changed_files,
            _get_recent_checkpoints,
        )
        from datetime import datetime as _dt

        session_summary = str(arguments.get("session_summary", ""))
        first_next_action = str(arguments.get("first_next_action", ""))
        completed_work = arguments.get("completed_work")
        unfinished_work = arguments.get("unfinished_work")
        raw_dc = arguments.get("decision_context")
        notes = arguments.get("notes")

        if not session_summary or not first_next_action:
            return [
                types.TextContent(
                    type="text",
                    text="오류: session_summary와 first_next_action은 필수 항목입니다.",
                )
            ]

        # 체크포인트 참조
        checkpoints = _get_recent_checkpoints(root, n=1)
        latest_cp = checkpoints[0]["message"] if checkpoints else None

        # summary에 notes 병합
        full_summary = session_summary
        if notes:
            full_summary = f"{session_summary} | {notes}"

        decision_context = None
        if isinstance(raw_dc, dict):
            decision_context = {
                "tried": str(raw_dc.get("tried", "") or "(not provided)"),
                "blocked_by": str(raw_dc.get("blocked_by", "") or "(not provided)"),
                "switched_to": str(raw_dc.get("switched_to", "") or "(not provided)"),
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
                    "changed_files": _get_changed_files(root),
                    "completed_work": str(completed_work) if completed_work else None,
                    "unfinished_work": str(unfinished_work)
                    if unfinished_work
                    else None,
                    "first_next_action": first_next_action,
                    "decision_context": decision_context,
                    "latest_checkpoint": latest_cp,
                },
            ),
        )

        from vibelign.commands.vib_transfer_cmd import (
            _inject_agents_handoff_instruction,
        )

        content = _build_context_content(root, handoff_data=handoff_data)
        ctx_path = root / "PROJECT_CONTEXT.md"
        ctx_path.write_text(content, encoding="utf-8")
        _inject_agents_handoff_instruction(root)
        return [
            types.TextContent(
                type="text",
                text=(
                    "✓ Session Handoff 블록 생성 완료\n"
                    f"  파일: {ctx_path}\n"
                    "  새 AI에게 PROJECT_CONTEXT.md 상단의 Session Handoff 블록을 읽혀주세요."
                ),
            )
        ]

    # ── project_context_get ────────────────────────────────────────────────
    if name == "project_context_get":
        from vibelign.commands.vib_transfer_cmd import (
            _build_context_content,
            _TRANSFER_MARKER,
        )

        compact = bool(arguments.get("compact", False))
        full = bool(arguments.get("full", False))
        ctx_path = root / "PROJECT_CONTEXT.md"

        # 파일이 있으면 그대로 읽어서 반환 (handoff 블록 보존)
        # compact/full 옵션은 파일이 없을 때만 재생성에 사용됨
        if ctx_path.exists() and not compact and not full:
            content = ctx_path.read_text(encoding="utf-8")
        else:
            content = _build_context_content(root, compact=compact, full=full)

        return [types.TextContent(type="text", text=content)]

    # ── doctor_run ─────────────────────────────────────────────────────────
    if name == "doctor_run":
        from vibelign.core.doctor_v2 import build_doctor_envelope, render_doctor_json

        strict = bool(arguments.get("strict", False))
        envelope = build_doctor_envelope(root, strict=strict)
        return [types.TextContent(type="text", text=render_doctor_json(envelope))]

    # ── guard_check ────────────────────────────────────────────────────────
    if name == "guard_check":
        from vibelign.commands.vib_guard_cmd import _build_guard_envelope
        from vibelign.core.meta_paths import MetaPaths

        strict = bool(arguments.get("strict", False))
        since_minutes = int(cast(int | str, arguments.get("since_minutes", 30)))
        meta = MetaPaths(root)
        envelope = _build_guard_envelope(
            root, strict=strict, since_minutes=since_minutes
        )
        session = _load_patch_session(meta)
        if session is not None and bool(session.get("needs_verification")):
            raw_data = cast(object, envelope.get("data", {}))
            data = raw_data if isinstance(raw_data, dict) else {}
            data = cast(dict[str, object], data)
            if str(data.get("status", "")) != "fail":
                session["needs_verification"] = False
                session["verified_at"] = _patch_session_now()
                session["guard_status"] = str(data.get("status", ""))
                _save_patch_session(meta, session)
        return [
            types.TextContent(
                type="text",
                text=json.dumps(envelope, indent=2, ensure_ascii=False),
            )
        ]

    # ── protect_add ────────────────────────────────────────────────────────
    if name == "protect_add":
        from vibelign.core.protected_files import get_protected, save_protected

        raw_file_paths = arguments.get("file_paths", [])
        file_paths = (
            [str(item) for item in raw_file_paths]
            if isinstance(raw_file_paths, list)
            else []
        )
        if not file_paths:
            return [
                types.TextContent(type="text", text="오류: file_paths가 필요합니다.")
            ]
        protected = get_protected(root)
        new_paths = [p for p in file_paths if p not in protected]
        protected.update(new_paths)
        save_protected(root, protected)
        lines = [f"✓ {len(new_paths)}개 파일을 보호 목록에 추가했습니다."]
        lines.extend(f"  - {p}" for p in new_paths)
        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── patch_get ──────────────────────────────────────────────────────────
    if name == "patch_get":
        from vibelign.commands.vib_patch_cmd import _build_patch_data
        from vibelign.core.meta_paths import MetaPaths

        request = str(arguments.get("request", ""))
        if not request:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "ok": False,
                            "error": "request가 필요합니다.",
                            "data": None,
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                )
            ]
        lazy_fanout = bool(arguments.get("lazy_fanout"))
        meta = MetaPaths(root)
        active_session = _load_patch_session(meta)
        verification_blocked = bool(
            active_session and active_session.get("needs_verification")
        )
        data = _build_patch_data(root, request, lazy_fanout=lazy_fanout)
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
                    (active_session or {}).get("session_id") or _new_patch_session_id()
                ),
                "request": request,
                "target_file": patch_plan["target_file"],
                "target_anchor": patch_plan["target_anchor"],
                "sub_intents": sub_intents,
                "pending_sub_intents": pending_sub_intents,
                "step_count": len(step_list),
                "needs_verification": False,
                "active": True,
                "updated_at": _patch_session_now(),
            }
            _save_patch_session(meta, session)
        result = {
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
            contract["status"] = "NEEDS_CLARIFICATION"
            questions = cast(list[object], result.get("clarifying_questions") or [])
            questions = [str(item) for item in questions if str(item).strip()]
            blocked_question = (
                "이전 패치를 적용한 뒤 아직 guard_check로 검증하지 않았어요. "
                "다음 단계로 가기 전에 guard_check를 먼저 실행해 주세요."
            )
            if blocked_question not in questions:
                questions.append(blocked_question)
            result["clarifying_questions"] = questions
            result["session_blocked"] = True
        elif session is not None:
            result["session"] = session
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False),
            )
        ]

    if name == "patch_apply":
        from vibelign.core.strict_patch import apply_strict_patch
        from vibelign.core.meta_paths import MetaPaths

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
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "ok": False,
                            "error": "strict_patch JSON object가 필요합니다.",
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                )
            ]
        result = apply_strict_patch(
            root,
            strict_patch,
            dry_run=bool(arguments.get("dry_run")),
        )
        meta = MetaPaths(root)
        session = _load_patch_session(meta)
        if (
            session is not None
            and bool(result.get("ok"))
            and not bool(result.get("dry_run"))
        ):
            session["needs_verification"] = True
            session["verified_at"] = None
            session["last_applied_at"] = _patch_session_now()
            session["applied_operation_count"] = result.get("applied_operation_count")
            session["active"] = True
            _save_patch_session(meta, session)
            result["session"] = session
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False),
            )
        ]

    # ── anchor_run ─────────────────────────────────────────────────────────
    if name == "anchor_run":
        from vibelign.core.anchor_tools import (
            recommend_anchor_targets,
            insert_module_anchors,
            collect_anchor_index,
            collect_anchor_metadata,
        )
        from vibelign.core.meta_paths import MetaPaths
        from vibelign.core.project_map import load_project_map
        from datetime import datetime, timezone

        meta = MetaPaths(root)
        meta.ensure_vibelign_dirs()
        project_map, _ = load_project_map(root)
        recommendations = recommend_anchor_targets(
            root, allowed_exts=None, project_map=project_map
        )
        targets = [root / str(item["path"]) for item in recommendations]
        changed = []
        for path in targets:
            if insert_module_anchors(path):
                changed.append(str(path.relative_to(root)))
        # 앵커 인덱스 갱신
        index = collect_anchor_index(root, allowed_exts=None)
        metadata = collect_anchor_metadata(root, allowed_exts=None)
        payload = {"schema_version": 1, "anchors": index, "files": metadata}
        meta.anchor_index_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        # 상태 갱신
        if meta.state_path.exists():
            state = json.loads(meta.state_path.read_text(encoding="utf-8"))
            state["last_anchor_run_at"] = datetime.now(timezone.utc).isoformat()
            meta.state_path.write_text(
                json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        if changed:
            text = f"✓ 앵커 삽입 완료 — {len(changed)}개 파일\n" + "\n".join(
                f"  - {f}" for f in changed
            )
        else:
            text = "모든 파일에 이미 앵커가 있습니다."
        return [types.TextContent(type="text", text=text)]

    # ── explain_get ────────────────────────────────────────────────────────
    if name == "explain_get":
        from vibelign.commands.vib_explain_cmd import _build_explain_envelope

        since_minutes = int(cast(int | str, arguments.get("since_minutes", 120)))
        envelope = _build_explain_envelope(root, since_minutes=since_minutes)
        return [
            types.TextContent(
                type="text",
                text=json.dumps(envelope, indent=2, ensure_ascii=False),
            )
        ]

    # ── anchor_list ────────────────────────────────────────────────────────
    if name == "anchor_list":
        from vibelign.core.meta_paths import MetaPaths

        meta = MetaPaths(root)
        if not meta.anchor_index_path.exists():
            return [
                types.TextContent(
                    type="text",
                    text="앵커 인덱스가 없습니다. `vib scan`을 먼저 실행하세요.",
                )
            ]
        data = json.loads(meta.anchor_index_path.read_text(encoding="utf-8"))
        return [
            types.TextContent(
                type="text",
                text=json.dumps(data, indent=2, ensure_ascii=False),
            )
        ]

    # ── config_get ─────────────────────────────────────────────────────────
    if name == "config_get":
        from vibelign.core.meta_paths import MetaPaths

        meta = MetaPaths(root)
        if not meta.config_path.exists():
            return [
                types.TextContent(
                    type="text",
                    text="설정 파일이 없습니다. `vib init`을 먼저 실행하세요.",
                )
            ]
        text = meta.config_path.read_text(encoding="utf-8")
        return [types.TextContent(type="text", text=text)]

    # ── doctor_plan ────────────────────────────────────────────────────────
    if name == "doctor_plan":
        import json as _json
        from vibelign.core.doctor_v2 import analyze_project_v2
        from vibelign.action_engine.action_planner import generate_plan

        strict = bool(arguments.get("strict", False))
        report = analyze_project_v2(root, strict=strict)
        plan = generate_plan(report)
        return [
            types.TextContent(
                type="text",
                text=_json.dumps(plan.to_dict(), indent=2, ensure_ascii=False),
            )
        ]

    # ── doctor_patch ───────────────────────────────────────────────────────
    if name == "doctor_patch":
        from vibelign.core.doctor_v2 import analyze_project_v2
        from vibelign.action_engine.action_planner import generate_plan
        from vibelign.action_engine.generators.patch_generator import (
            generate_patch_preview,
        )

        strict = bool(arguments.get("strict", False))
        report = analyze_project_v2(root, strict=strict)
        plan = generate_plan(report)
        preview = generate_patch_preview(plan, root)
        return [types.TextContent(type="text", text=preview)]

    # ── doctor_apply ───────────────────────────────────────────────────────
    if name == "doctor_apply":
        import json as _json
        from vibelign.core.doctor_v2 import analyze_project_v2
        from vibelign.action_engine.action_planner import generate_plan
        from vibelign.action_engine.executors.action_executor import execute_plan

        strict = bool(arguments.get("strict", False))
        report = analyze_project_v2(root, strict=strict)
        plan = generate_plan(report)
        result = execute_plan(plan, root, force=True, quiet=True)
        output = {
            "ok": not result.aborted,
            "checkpoint_id": result.checkpoint_id,
            "done": result.done_count,
            "manual": result.manual_count,
            "results": [
                {
                    "action_type": r.action.action_type,
                    "status": r.status,
                    "detail": r.detail,
                }
                for r in result.results
            ],
        }
        return [
            types.TextContent(
                type="text", text=_json.dumps(output, indent=2, ensure_ascii=False)
            )
        ]

    return [types.TextContent(type="text", text=f"알 수 없는 도구: {name}")]


# === ANCHOR: MCP_SERVER_CALL_TOOL_END ===


# === ANCHOR: MCP_SERVER_MAIN_START ===
async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(_run())


# === ANCHOR: MCP_SERVER_MAIN_END ===


if __name__ == "__main__":
    main()
# === ANCHOR: MCP_SERVER_END ===
