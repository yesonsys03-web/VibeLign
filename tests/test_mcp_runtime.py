import asyncio
import importlib
import unittest
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import cast


mcp_runtime = importlib.import_module("vibelign.mcp.mcp_runtime")
resolve_runtime_root = cast(
    Callable[[Callable[[], Path], Callable[[Path], Path]], Path],
    mcp_runtime.resolve_runtime_root,
)
run_async_entry = cast(
    Callable[[Callable[[], Coroutine[object, object, None]]], None],
    mcp_runtime.run_async_entry,
)
run_stdio_app = cast(
    Callable[[object, Callable[[], object]], Coroutine[object, object, None]],
    mcp_runtime.run_stdio_app,
)


class FakeServerContext:
    async def __aenter__(self) -> tuple[str, str]:
        return ("reader", "writer")

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class FakeApp:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object]] = []

    async def run(
        self, read_stream: object, write_stream: object, init_options: object
    ) -> None:
        self.calls.append((read_stream, write_stream, init_options))

    def create_initialization_options(self) -> dict[str, str]:
        return {"server": "ok"}


class McpRuntimeTest(unittest.TestCase):
    def test_resolve_runtime_root_uses_cwd_and_project_resolver(self) -> None:
        result = resolve_runtime_root(
            lambda: Path("/tmp/work"), lambda path: path / "root"
        )
        self.assertEqual(result, Path("/tmp/work/root"))

    def test_run_stdio_app_invokes_app_with_context_streams(self) -> None:
        app = FakeApp()
        asyncio.run(run_stdio_app(app, lambda: FakeServerContext()))
        self.assertEqual(app.calls, [("reader", "writer", {"server": "ok"})])

    def test_run_async_entry_executes_coroutine_factory(self) -> None:
        called: list[str] = []

        async def entry() -> None:
            called.append("done")

        run_async_entry(entry)
        self.assertEqual(called, ["done"])


if __name__ == "__main__":
    _ = unittest.main()
