import asyncio
import importlib
import sys
import types as py_types
import unittest
from collections.abc import Awaitable, Coroutine
from dataclasses import dataclass
from typing import Callable, cast


@dataclass
class _FakeTool:
    name: str
    description: str
    inputSchema: dict[str, object]


@dataclass
class _FakeTextContent:
    type: str
    text: str


class _FakeServer:
    def __init__(self, _name: str) -> None:
        self._list_tools_handler: Callable[[], Awaitable[list[_FakeTool]]] | None = None

    def list_tools(
        self,
    ) -> Callable[
        [Callable[[], Awaitable[list[_FakeTool]]]],
        Callable[[], Awaitable[list[_FakeTool]]],
    ]:
        def decorator(
            func: Callable[[], Awaitable[list[_FakeTool]]],
        ) -> Callable[[], Awaitable[list[_FakeTool]]]:
            self._list_tools_handler = func
            return func

        return decorator

    def call_tool(self) -> Callable[[Callable[..., object]], Callable[..., object]]:
        def decorator(func: Callable[..., object]) -> Callable[..., object]:
            return func

        return decorator


def _install_fake_mcp_modules() -> None:
    fake_mcp = py_types.ModuleType("mcp")
    fake_server = py_types.ModuleType("mcp.server")
    fake_stdio = py_types.ModuleType("mcp.server.stdio")
    fake_types = py_types.ModuleType("mcp.types")

    setattr(fake_server, "Server", _FakeServer)
    setattr(fake_stdio, "stdio_server", object())
    setattr(fake_types, "Tool", _FakeTool)
    setattr(fake_types, "TextContent", _FakeTextContent)

    sys.modules["mcp"] = fake_mcp
    sys.modules["mcp.server"] = fake_server
    sys.modules["mcp.server.stdio"] = fake_stdio
    sys.modules["mcp.types"] = fake_types


_install_fake_mcp_modules()
mcp_server = importlib.import_module("vibelign.mcp.mcp_server")
list_tools = cast(
    Callable[[], Coroutine[object, object, list[_FakeTool]]], mcp_server.list_tools
)


class McpToolSnapshotTest(unittest.TestCase):
    def test_list_tools_exposes_expected_tool_names_in_order(self) -> None:
        tools = asyncio.run(list_tools())

        self.assertEqual(
            [tool.name for tool in tools],
            [
                "checkpoint_create",
                "checkpoint_list",
                "checkpoint_restore",
                "project_context_get",
                "doctor_run",
                "guard_check",
                "protect_add",
                "patch_get",
                "patch_apply",
                "handoff_create",
                "anchor_run",
                "anchor_list",
                "anchor_auto_intent",
                "anchor_set_intent",
                "transfer_set_decision",
                "transfer_set_verification",
                "transfer_set_relevant",
                "anchor_get_meta",
                "explain_get",
                "config_get",
                "doctor_plan",
                "doctor_patch",
                "doctor_apply",
            ],
        )

    def test_critical_tool_required_fields_snapshot(self) -> None:
        tools = asyncio.run(list_tools())
        by_name = {tool.name: tool for tool in tools}

        self.assertEqual(
            cast(
                list[str], by_name["checkpoint_create"].inputSchema.get("required", [])
            ),
            ["message"],
        )
        self.assertEqual(
            cast(
                list[str], by_name["checkpoint_restore"].inputSchema.get("required", [])
            ),
            ["checkpoint_id"],
        )
        self.assertEqual(
            cast(list[str], by_name["protect_add"].inputSchema.get("required", [])),
            ["file_paths"],
        )
        self.assertEqual(
            cast(list[str], by_name["patch_get"].inputSchema.get("required", [])),
            ["request"],
        )
        self.assertEqual(
            cast(list[str], by_name["patch_apply"].inputSchema.get("required", [])),
            ["strict_patch"],
        )
        self.assertEqual(
            cast(list[str], by_name["handoff_create"].inputSchema.get("required", [])),
            ["session_summary", "first_next_action"],
        )
        self.assertEqual(by_name["transfer_set_decision"].inputSchema["required"], ["text"])
        self.assertEqual(by_name["transfer_set_verification"].inputSchema["required"], ["text"])
        self.assertEqual(by_name["transfer_set_relevant"].inputSchema["required"], ["path"])


if __name__ == "__main__":
    _ = unittest.main()
