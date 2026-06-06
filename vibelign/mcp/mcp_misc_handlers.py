# === ANCHOR: MCP_MISC_HANDLERS_START ===
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.meta_paths import MetaPaths


# === ANCHOR: MCP_MISC_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_MISC_HANDLERS___CALL___START ===
# === ANCHOR: MCP_MISC_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_MISC_HANDLERS___CALL___END ===


# === ANCHOR: MCP_MISC_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_MISC_HANDLERS__TEXT_END ===


# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_EXPLAIN_GET_START ===
def handle_explain_get(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_EXPLAIN_GET_END ===
) -> list[object]:
    from vibelign.commands.vib_explain_cmd import build_explain_envelope

    since_minutes = int(cast(int | str, arguments.get("since_minutes", 120)))
    envelope = build_explain_envelope(root, since_minutes=since_minutes)
    return _text(text_content, json.dumps(envelope, indent=2, ensure_ascii=False))


# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_ANCHOR_LIST_START ===
def handle_anchor_list(root: Path, text_content: TextContentFactory) -> list[object]:
    meta = MetaPaths(root)
    if not meta.anchor_index_path.exists():
        return _text(
            text_content, "앵커 인덱스가 없습니다. `vib scan`을 먼저 실행하세요."
        )
    data = cast(object, json.loads(meta.anchor_index_path.read_text(encoding="utf-8")))
    return _text(text_content, json.dumps(data, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_ANCHOR_LIST_END ===


# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_CONFIG_GET_START ===
def handle_config_get(root: Path, text_content: TextContentFactory) -> list[object]:
    meta = MetaPaths(root)
    if not meta.config_path.exists():
        return _text(
            text_content, "설정 파일이 없습니다. `vib init`을 먼저 실행하세요."
        )
    return _text(text_content, meta.config_path.read_text(encoding="utf-8"))
# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_CONFIG_GET_END ===


# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_PROJECT_MAP_GET_START ===
def handle_project_map_get(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    map_path = MetaPaths(root).project_map_path
    if not map_path.is_file():
        payload = {
            "ok": False,
            "error": "project_map.json not found — run `vib doctor` to generate it",
            "data": None,
        }
        return _text(text_content, json.dumps(payload, ensure_ascii=False))
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = {
            "ok": False,
            "error": f"project_map.json could not be read ({type(exc).__name__})",
            "data": None,
        }
        return _text(text_content, json.dumps(payload, ensure_ascii=False))
    if not isinstance(data, dict):
        payload = {
            "ok": False,
            "error": "project_map.json has unexpected shape (expected JSON object)",
            "data": None,
        }
        return _text(text_content, json.dumps(payload, ensure_ascii=False))
    payload = {"ok": True, "error": None, "data": data}
    return _text(text_content, json.dumps(payload, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_PROJECT_MAP_GET_END ===


# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_PLANNING_GET_START ===
def handle_planning_get(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    planning_dir = MetaPaths(root).vibelign_dir / "planning"
    if not planning_dir.is_dir():
        return _text(
            text_content,
            "저장된 기획안이 없습니다. 기획방에서 기획안을 만들어 저장하세요.",
        )

    requested = arguments.get("session_id")
    wanted_id = (
        requested.strip()
        if isinstance(requested, str) and requested.strip()
        else None
    )

    best: tuple[str, float] | None = None
    best_output: str | None = None
    best_sid: str | None = None
    for session_path in planning_dir.glob("*/session.json"):
        try:
            raw = cast(object, json.loads(session_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        session = cast(dict[str, object], raw)
        sid = str(session.get("session_id") or session_path.parent.name)
        if wanted_id is not None and sid != wanted_id:
            continue
        output_path = session.get("output_path")
        # GUI 채팅 세션은 저장 전 output_path=None 이므로, 실제 plan 파일이
        # 존재하는 세션만 후보로 삼는다 (빈 세션이 최신을 가리지 않도록).
        if not isinstance(output_path, str) or not output_path.strip():
            continue
        if not (root / output_path).is_file():
            continue
        created_at = session.get("created_at")
        created_key = created_at if isinstance(created_at, str) else ""
        try:
            mtime = session_path.stat().st_mtime
        except OSError:
            mtime = 0.0
        sort_key = (created_key, mtime)
        if best is None or sort_key > best:
            best = sort_key
            best_output = output_path
            best_sid = sid

    if best_output is None or best_sid is None:
        hint = f" (session_id={wanted_id})" if wanted_id is not None else ""
        return _text(
            text_content,
            f"저장된 기획안을 찾을 수 없습니다{hint}. 기획방에서 기획안을 만들어 저장하세요.",
        )

    markdown = (root / best_output).read_text(encoding="utf-8")
    header = (
        f"<!-- VibeLign 기획안 | session_id={best_sid} | source={best_output} -->\n\n"
    )
    return _text(text_content, header + markdown)
# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_PLANNING_GET_END ===
# === ANCHOR: MCP_MISC_HANDLERS_END ===
