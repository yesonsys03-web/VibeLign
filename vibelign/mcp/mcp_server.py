# === ANCHOR: MCP_SERVER_START ===
"""VibeLign MCP Server — stdio transport.

사용법:
    vibelign-mcp          # 설치 후 직접 실행
    python -m vibelign.mcp.mcp_server

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

import importlib
from pathlib import Path
from collections.abc import Callable, Coroutine
from typing import Protocol, cast


from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from vibelign.core.project_root import resolve_project_root
from vibelign.mcp.mcp_tool_specs import ToolSpec


app = Server("vibelign")


class ToolSpecsModule(Protocol):
    TOOL_SPECS: tuple[ToolSpec, ...]


class DispatchModule(Protocol):
    async def call_tool_dispatch(
        self,
        name: str,
        arguments: dict[str, object],
        *,
        root: Path,
        text_content: object,
    ) -> list[types.TextContent]: ...


class ToolLoaderModule(Protocol):
    def build_tools(
        self, tool_specs_module: ToolSpecsModule, tool_factory: object
    ) -> list[types.Tool]: ...


def _root() -> Path:
    resolve_runtime_root = cast(
        Callable[[Callable[[], Path], Callable[[Path], Path]], Path],
        importlib.import_module("vibelign.mcp.mcp_runtime").resolve_runtime_root,
    )
    return resolve_runtime_root(Path.cwd, resolve_project_root)


# === ANCHOR: MCP_SERVER_LIST_TOOLS_START ===
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    tool_loader = cast(
        ToolLoaderModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_tool_loader")),
    )
    tool_specs_module = cast(
        ToolSpecsModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_tool_specs")),
    )
    return tool_loader.build_tools(tool_specs_module, types.Tool)


# === ANCHOR: MCP_SERVER_LIST_TOOLS_END ===


# === ANCHOR: MCP_SERVER_CALL_TOOL_START ===
@app.call_tool()
async def call_tool(name: str, arguments: dict[str, object]) -> list[types.TextContent]:
    dispatch_module = cast(
        DispatchModule,
        cast(object, importlib.import_module("vibelign.mcp.mcp_dispatch")),
    )
    return await dispatch_module.call_tool_dispatch(
        name,
        arguments,
        root=_root(),
        text_content=types.TextContent,
    )


# === ANCHOR: MCP_SERVER_CALL_TOOL_END ===


# === ANCHOR: MCP_SERVER_MAIN_START ===
async def _run() -> None:
    run_stdio_app = cast(
        Callable[[object, Callable[[], object]], Coroutine[object, object, None]],
        importlib.import_module("vibelign.mcp.mcp_runtime").run_stdio_app,
    )
    await run_stdio_app(app, stdio_server)


def main() -> None:
    run_async_entry = cast(
        Callable[[Callable[[], object]], None],
        importlib.import_module("vibelign.mcp.mcp_runtime").run_async_entry,
    )
    run_async_entry(_run)


# === ANCHOR: MCP_SERVER_MAIN_END ===


if __name__ == "__main__":
    main()
# === ANCHOR: MCP_SERVER_END ===
