# === ANCHOR: MCP_PROTECT_HANDLERS_START ===
from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast


# === ANCHOR: MCP_PROTECT_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_PROTECT_HANDLERS___CALL___START ===
# === ANCHOR: MCP_PROTECT_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_PROTECT_HANDLERS___CALL___END ===


# === ANCHOR: MCP_PROTECT_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_PROTECT_HANDLERS__TEXT_END ===


# === ANCHOR: MCP_PROTECT_HANDLERS_HANDLE_PROTECT_ADD_START ===
def handle_protect_add(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_PROTECT_HANDLERS_HANDLE_PROTECT_ADD_END ===
) -> list[object]:
    from vibelign.core.protected_files import get_protected, save_protected

    raw_file_paths = arguments.get("file_paths", [])
    file_paths = (
        [str(item) for item in cast(list[object], raw_file_paths)]
        if isinstance(raw_file_paths, list)
        else []
    )
    if not file_paths:
        return _text(text_content, "오류: file_paths가 필요합니다.")
    protected = get_protected(root)
    new_paths = [path for path in file_paths if path not in protected]
    protected.update(new_paths)
    save_protected(root, protected)
    lines = [f"✓ {len(new_paths)}개 파일을 보호 목록에 추가했습니다."]
    lines.extend(f"  - {path}" for path in new_paths)
    return _text(text_content, "\n".join(lines))
# === ANCHOR: MCP_PROTECT_HANDLERS_END ===
