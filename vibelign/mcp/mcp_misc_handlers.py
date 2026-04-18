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
# === ANCHOR: MCP_MISC_HANDLERS_END ===
