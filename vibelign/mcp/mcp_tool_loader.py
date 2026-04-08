# === ANCHOR: MCP_TOOL_LOADER_START ===
from __future__ import annotations

from typing import Protocol

from vibelign.mcp.mcp_tool_specs import ToolSpec


# === ANCHOR: MCP_TOOL_LOADER_TOOLFACTORY_START ===
class ToolFactory(Protocol):
    # === ANCHOR: MCP_TOOL_LOADER___CALL___START ===
    def __call__(
        self, *, name: str, description: str, inputSchema: dict[str, object]
# === ANCHOR: MCP_TOOL_LOADER_TOOLFACTORY_END ===
    # === ANCHOR: MCP_TOOL_LOADER___CALL___END ===
    ) -> object: ...


# === ANCHOR: MCP_TOOL_LOADER_TOOLSPECSMODULE_START ===
class ToolSpecsModule(Protocol):
    TOOL_SPECS: tuple[ToolSpec, ...]
# === ANCHOR: MCP_TOOL_LOADER_TOOLSPECSMODULE_END ===


# === ANCHOR: MCP_TOOL_LOADER_BUILD_TOOLS_START ===
def build_tools(
    tool_specs_module: ToolSpecsModule,
    tool_factory: ToolFactory,
# === ANCHOR: MCP_TOOL_LOADER_BUILD_TOOLS_END ===
) -> list[object]:
    return [
        tool_factory(
            name=spec["name"],
            description=spec["description"],
            inputSchema=spec["inputSchema"],
        )
        for spec in tool_specs_module.TOOL_SPECS
    ]
# === ANCHOR: MCP_TOOL_LOADER_END ===
