# === ANCHOR: MEMORY_CAPABILITY_GRANTS_START ===
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast


GrantStatus = Literal["granted"]


@dataclass(frozen=True)
class CapabilityGrantRecord:
    grant_id: str
    tool: str
    capability: str
    status: GrantStatus = "granted"


def capability_grants_path(root: Path) -> Path:
    return root / ".vibelign" / "mcp_capability_grants.json"


def load_capability_grants(root: Path) -> list[CapabilityGrantRecord]:
    path = capability_grants_path(root)
    if not path.exists():
        return []
    try:
        loaded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []
    if not isinstance(loaded, dict):
        return []
    raw_loaded = cast(dict[object, object], loaded)
    raw_grants = raw_loaded.get("grants")
    if not isinstance(raw_grants, list):
        return []
    grants: list[CapabilityGrantRecord] = []
    for item in cast(list[object], raw_grants):
        grant = _grant_from_raw(item)
        if grant is not None:
            grants.append(grant)
    return grants


def is_capability_granted(root: Path, tool: str, capability: str) -> bool:
    tool_name = _safe_label(tool)
    capability_name = _safe_label(capability)
    if not tool_name or not capability_name:
        return False
    return any(
        grant.tool == tool_name
        and grant.capability == capability_name
        and grant.status == "granted"
        for grant in load_capability_grants(root)
    )


def add_capability_grant(root: Path, tool: str, capability: str) -> CapabilityGrantRecord:
    tool_name = _safe_label(tool)
    capability_name = _safe_label(capability)
    if not tool_name or not capability_name:
        raise ValueError("tool and capability are required")
    grants = load_capability_grants(root)
    for grant in grants:
        if grant.tool == tool_name and grant.capability == capability_name:
            return grant
    grant = CapabilityGrantRecord(
        grant_id=f"grant_{uuid.uuid4().hex}",
        tool=tool_name,
        capability=capability_name,
    )
    _save_capability_grants(root, grants + [grant])
    return grant


def revoke_capability_grant(root: Path, tool: str, capability: str) -> bool:
    tool_name = _safe_label(tool)
    capability_name = _safe_label(capability)
    if not tool_name or not capability_name:
        return False
    grants = load_capability_grants(root)
    kept = [
        grant
        for grant in grants
        if not (grant.tool == tool_name and grant.capability == capability_name)
    ]
    if len(kept) == len(grants):
        return False
    _save_capability_grants(root, kept)
    return True


def _save_capability_grants(root: Path, grants: list[CapabilityGrantRecord]) -> None:
    path = capability_grants_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "grants": [
            {
                "grant_id": grant.grant_id,
                "tool": grant.tool,
                "capability": grant.capability,
                "status": grant.status,
            }
            for grant in grants
        ]
    }
    tmp_path = path.with_suffix(".tmp")
    _ = tmp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _ = tmp_path.replace(path)


def _grant_from_raw(item: object) -> CapabilityGrantRecord | None:
    if not isinstance(item, dict):
        return None
    raw = cast(dict[object, object], item)
    grant_id = _safe_label(raw.get("grant_id"))
    tool = _safe_label(raw.get("tool"))
    capability = _safe_label(raw.get("capability"))
    status = raw.get("status")
    if not grant_id or not tool or not capability or status != "granted":
        return None
    return CapabilityGrantRecord(
        grant_id=grant_id,
        tool=tool,
        capability=capability,
        status="granted",
    )


def _safe_label(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(ch for ch in value.strip() if ch.isalnum() or ch in {"_", "-", ":"})[:80]
# === ANCHOR: MEMORY_CAPABILITY_GRANTS_END ===
