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
from pathlib import Path
from typing import cast

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types


app = Server("vibelign")


def _root() -> Path:
    return Path.cwd()


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
                    }
                },
                "required": ["request"],
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

    # ── project_context_get ────────────────────────────────────────────────
    if name == "project_context_get":
        from vibelign.commands.vib_transfer_cmd import _build_context_content

        compact = bool(arguments.get("compact", False))
        full = bool(arguments.get("full", False))
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

        strict = bool(arguments.get("strict", False))
        since_minutes = int(cast(int | str, arguments.get("since_minutes", 30)))
        envelope = _build_guard_envelope(
            root, strict=strict, since_minutes=since_minutes
        )
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
        from vibelign.commands.vib_patch_cmd import _build_patch_data, _build_contract

        request = str(arguments.get("request", ""))
        if not request:
            return [types.TextContent(type="text", text="오류: request가 필요합니다.")]
        data = _build_patch_data(root, request)
        patch_plan = data["patch_plan"]
        contract = _build_contract(patch_plan)
        result = {
            "target_file": patch_plan["target_file"],
            "target_anchor": patch_plan["target_anchor"],
            "codespeak": patch_plan["codespeak"],
            "interpretation": patch_plan["interpretation"],
            "confidence": patch_plan["confidence"],
            "constraints": patch_plan["constraints"],
            "allowed_ops": contract["allowed_ops"],
            "status": contract["status"],
            "clarifying_questions": contract["clarifying_questions"],
            "rationale": patch_plan["rationale"],
        }
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
