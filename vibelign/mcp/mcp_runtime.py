# === ANCHOR: MCP_RUNTIME_START ===
from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Protocol


# === ANCHOR: MCP_RUNTIME_STDIOCONTEXT_START ===
class StdioContext(Protocol):
    # === ANCHOR: MCP_RUNTIME___AENTER___START ===
    async def __aenter__(self) -> tuple[object, object]: ...
# === ANCHOR: MCP_RUNTIME_STDIOCONTEXT_END ===
    # === ANCHOR: MCP_RUNTIME___AENTER___END ===
    # === ANCHOR: MCP_RUNTIME___AEXIT___START ===
    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool: ...
    # === ANCHOR: MCP_RUNTIME___AEXIT___END ===


# === ANCHOR: MCP_RUNTIME_RUNNABLEAPP_START ===
class RunnableApp(Protocol):
    # === ANCHOR: MCP_RUNTIME_RUN_START ===
    async def run(
        self, read_stream: object, write_stream: object, init_options: object
    # === ANCHOR: MCP_RUNTIME_RUN_END ===
    ) -> None: ...
# === ANCHOR: MCP_RUNTIME_RUNNABLEAPP_END ===

    # === ANCHOR: MCP_RUNTIME_CREATE_INITIALIZATION_OPTIONS_START ===
    def create_initialization_options(self) -> object: ...
    # === ANCHOR: MCP_RUNTIME_CREATE_INITIALIZATION_OPTIONS_END ===


# === ANCHOR: MCP_RUNTIME_RESOLVE_RUNTIME_ROOT_START ===
def resolve_runtime_root(
    cwd_factory: Callable[[], Path],
    project_root_resolver: Callable[[Path], Path],
# === ANCHOR: MCP_RUNTIME_RESOLVE_RUNTIME_ROOT_END ===
) -> Path:
    return project_root_resolver(cwd_factory())


# === ANCHOR: MCP_RUNTIME_RUN_STDIO_APP_START ===
async def run_stdio_app(
    app: RunnableApp,
    stdio_server_factory: Callable[[], StdioContext],
# === ANCHOR: MCP_RUNTIME_RUN_STDIO_APP_END ===
) -> None:
    server_context = stdio_server_factory()
    async with server_context as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


# === ANCHOR: MCP_RUNTIME_RUN_ASYNC_ENTRY_START ===
def run_async_entry(entrypoint: Callable[[], Coroutine[object, object, None]]) -> None:
    asyncio.run(entrypoint())
# === ANCHOR: MCP_RUNTIME_RUN_ASYNC_ENTRY_END ===
# === ANCHOR: MCP_RUNTIME_END ===
