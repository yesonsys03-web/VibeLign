# === ANCHOR: VIB_MCP_CMD_START ===
from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from vibelign.core.memory.capability_grants import (
    add_capability_grant,
    load_capability_grants,
    revoke_capability_grant,
)
from vibelign.core.memory.capability_policy import get_capability_policy, is_known_capability
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import cli_print

print = cli_print


def run_vib_mcp_command(args: Namespace) -> int:
    action = str(getattr(args, "mcp_action", "") or "")
    if action == "grants":
        return _run_vib_mcp_grants()
    if action == "revoke":
        return _run_vib_mcp_revoke(args)
    if action != "grant":
        print("Usage: vib mcp grant <capability> --tool <tool> | vib mcp revoke <capability> --tool <tool> | vib mcp grants")
        return 2
    capability = str(getattr(args, "capability", "") or "")
    tool = str(getattr(args, "tool", "") or "")
    if not is_known_capability(capability):
        print(f"Unknown MCP capability: {capability}")
        return 2
    policy = get_capability_policy(capability)
    if policy.default_grant != "denied":
        print(f"MCP capability is already allowed by default: {capability}")
        return 2
    root = resolve_project_root(Path.cwd())
    try:
        grant = add_capability_grant(root, tool, capability)
    except ValueError:
        print("MCP tool name is required")
        return 2
    print(f"MCP capability grant saved: {grant.capability} for {grant.tool}")
    return 0


def _run_vib_mcp_revoke(args: Namespace) -> int:
    capability = str(getattr(args, "capability", "") or "")
    tool = str(getattr(args, "tool", "") or "")
    root = resolve_project_root(Path.cwd())
    removed = revoke_capability_grant(root, tool, capability)
    if not removed:
        print(f"No MCP capability grant matched: {capability} for {tool}")
        return 0
    print(f"MCP capability grant revoked: {capability} for {tool}")
    return 0


def _run_vib_mcp_grants() -> int:
    root = resolve_project_root(Path.cwd())
    grants = load_capability_grants(root)
    if not grants:
        print("No MCP capability grants.")
        return 0
    print(f"MCP capability grants ({len(grants)}):")
    for grant in grants:
        print(f"- {grant.capability} for {grant.tool} ({grant.status})")
    return 0
# === ANCHOR: VIB_MCP_CMD_END ===
