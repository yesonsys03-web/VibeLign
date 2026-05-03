# === ANCHOR: MEMORY_CAPABILITY_POLICY_START ===
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


CapabilityGrant = Literal["allowed", "denied"]


@dataclass(frozen=True)
class CapabilityPolicy:
    name: str
    default_grant: CapabilityGrant
    requires_explicit_grant: bool
    denied_call_writes_project_state: bool
    denied_message: str


_CAPABILITY_POLICIES: dict[str, CapabilityPolicy] = {
    "memory_summary_read": CapabilityPolicy(
        name="memory_summary_read",
        default_grant="allowed",
        requires_explicit_grant=False,
        denied_call_writes_project_state=False,
        denied_message="memory_summary_read is enabled as a redacted read-only summary.",
    ),
    "recovery_preview": CapabilityPolicy(
        name="recovery_preview",
        default_grant="allowed",
        requires_explicit_grant=False,
        denied_call_writes_project_state=False,
        denied_message="recovery_preview is enabled as a read-only recovery plan.",
    ),
    "checkpoint_create": CapabilityPolicy(
        name="checkpoint_create",
        default_grant="allowed",
        requires_explicit_grant=False,
        denied_call_writes_project_state=False,
        denied_message="checkpoint_create is enabled as the safe checkpoint write path.",
    ),
    "memory_full_read": CapabilityPolicy(
        name="memory_full_read",
        default_grant="denied",
        requires_explicit_grant=True,
        denied_call_writes_project_state=False,
        denied_message="memory_full_read is not enabled yet; use memory_summary_read for redacted read-only context.",
    ),
    "memory_write": CapabilityPolicy(
        name="memory_write",
        default_grant="denied",
        requires_explicit_grant=True,
        denied_call_writes_project_state=False,
        denied_message="memory_write is not enabled yet; use explicit CLI or transfer_set_* flows for confirmed memory updates.",
    ),
    "recovery_apply": CapabilityPolicy(
        name="recovery_apply",
        default_grant="denied",
        requires_explicit_grant=True,
        denied_call_writes_project_state=False,
        denied_message="recovery_apply is not enabled yet; use recovery_preview and checkpoint_create before any future apply flow.",
    ),
    "handoff_export": CapabilityPolicy(
        name="handoff_export",
        default_grant="denied",
        requires_explicit_grant=True,
        denied_call_writes_project_state=False,
        denied_message="handoff_export is not enabled yet; use project_context_get or handoff_create for local handoff context.",
    ),
}


def get_capability_policy(name: str) -> CapabilityPolicy:
    return _CAPABILITY_POLICIES.get(
        name,
        CapabilityPolicy(
            name=name,
            default_grant="denied",
            requires_explicit_grant=True,
            denied_call_writes_project_state=False,
            denied_message=f"{name} is not enabled yet.",
        ),
    )


def is_known_capability(name: str) -> bool:
    return name in _CAPABILITY_POLICIES
# === ANCHOR: MEMORY_CAPABILITY_POLICY_END ===
