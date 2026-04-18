# === ANCHOR: MCP_DISPATCH_START ===
from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from vibelign.mcp.mcp_handler_registry import DISPATCH_TABLE
from vibelign.mcp.mcp_handler_registry import TextContentFactory


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
    if handler is not None:
        return handler(root, arguments, text_content)
    return _text(text_content, f"알 수 없는 도구: {name}")
# === ANCHOR: MCP_DISPATCH_END ===
