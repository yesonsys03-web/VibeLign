# === ANCHOR: MCP_HEALTH_HANDLERS_START ===
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, cast


# === ANCHOR: MCP_HEALTH_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_HEALTH_HANDLERS___CALL___START ===
# === ANCHOR: MCP_HEALTH_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_HEALTH_HANDLERS___CALL___END ===


# === ANCHOR: MCP_HEALTH_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_HEALTH_HANDLERS__TEXT_END ===


# === ANCHOR: MCP_HEALTH_HANDLERS_HANDLE_DOCTOR_RUN_START ===
def handle_doctor_run(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_HEALTH_HANDLERS_HANDLE_DOCTOR_RUN_END ===
) -> list[object]:
    from vibelign.core.doctor_v2 import build_doctor_envelope, render_doctor_json

    strict = bool(arguments.get("strict", False))
    envelope = build_doctor_envelope(root, strict=strict)
    return _text(text_content, render_doctor_json(envelope))


# === ANCHOR: MCP_HEALTH_HANDLERS_HANDLE_GUARD_CHECK_START ===
def handle_guard_check(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_HEALTH_HANDLERS_HANDLE_GUARD_CHECK_END ===
) -> list[object]:
    from vibelign.commands.vib_guard_cmd import build_guard_envelope

    strict = bool(arguments.get("strict", False))
    since_minutes = int(cast(int | str, arguments.get("since_minutes", 30)))
    envelope = build_guard_envelope(root, strict=strict, since_minutes=since_minutes)
    return _text(text_content, json.dumps(envelope, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_HEALTH_HANDLERS_END ===
