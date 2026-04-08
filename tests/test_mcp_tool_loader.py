import importlib
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast


@dataclass
class FakeTool:
    name: str
    description: str
    inputSchema: dict[str, object]


from vibelign.mcp.mcp_tool_specs import ToolSpec


tool_loader = importlib.import_module("vibelign.mcp.mcp_tool_loader")
build_tools = cast(
    Callable[[object, type[FakeTool]], list[FakeTool]],
    tool_loader.build_tools,
)


class FakeToolSpecsModule:
    TOOL_SPECS: tuple[ToolSpec, ...] = (
        {
            "name": "alpha",
            "description": "first",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "beta",
            "description": "second",
            "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}},
        },
    )


class McpToolLoaderTest(unittest.TestCase):
    def test_build_tools_preserves_order(self) -> None:
        tools = build_tools(FakeToolSpecsModule, FakeTool)
        self.assertEqual([tool.name for tool in tools], ["alpha", "beta"])

    def test_build_tools_preserves_description_and_schema(self) -> None:
        tools = build_tools(FakeToolSpecsModule, FakeTool)
        properties = cast(dict[str, object], tools[1].inputSchema["properties"])
        self.assertEqual(tools[1].description, "second")
        self.assertIn("x", properties)


if __name__ == "__main__":
    _ = unittest.main()
