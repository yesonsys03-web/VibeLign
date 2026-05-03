# === ANCHOR: MCP_DENIED_HANDLERS_START ===
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.memory.capability_grants import is_capability_granted
from vibelign.core.memory.capability_policy import get_capability_policy


class TextContentFactory(Protocol):
    def __call__(self, *, type: str, text: str) -> object: ...


def handle_denied_capability(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
    *,
    capability: str,
) -> list[object]:
    _ = root
    _ = arguments
    policy = get_capability_policy(capability)
    tool = arguments.get("tool")
    grant_status = (
        "granted_but_not_enabled"
        if isinstance(tool, str) and is_capability_granted(root, tool, capability)
        else "not_granted"
    )
    payload: dict[str, object] = {
        "ok": False,
        "error": "permission_denied",
        "capability": capability,
        "read_only": True,
        "requires_explicit_grant": policy.requires_explicit_grant,
        "grant_status": grant_status,
        "grant_command_hint": f"vib mcp grant {capability} --tool <tool-name>",
        "message": policy.denied_message,
    }
    if capability == "recovery_apply":
        payload.update(_recovery_apply_readiness_payload(root, arguments))
    return [text_content(type="text", text=json.dumps(payload, ensure_ascii=False, sort_keys=True))]


def _recovery_apply_readiness_payload(root: Path, arguments: dict[str, object]) -> dict[str, object]:
    from vibelign.core.recovery.apply import RecoveryApplyRequest, check_recovery_apply_readiness

    request = RecoveryApplyRequest(
        checkpoint_id=str(arguments.get("checkpoint_id", "")),
        sandwich_checkpoint_id=str(arguments.get("sandwich_checkpoint_id", "")),
        paths=_string_list(arguments.get("paths")),
        preview_paths=_string_list(arguments.get("preview_paths")),
        confirmation=str(arguments.get("confirmation", "")),
        apply=arguments.get("apply") is True,
        feature_enabled=arguments.get("feature_enabled") is True,
    )
    readiness = check_recovery_apply_readiness(root, request)
    if readiness.busy:
        return {
            "readiness_status": "busy",
            **_instruction_boundary_payload(arguments),
            "operation_id": readiness.operation_id,
            "eta_seconds": readiness.eta_seconds,
            "validation_ok": readiness.validation.ok,
            "validation_errors": readiness.validation.errors,
            "normalized_paths": readiness.validation.normalized_paths,
            "safety_checkpoint_id": readiness.validation.summary.safety_checkpoint_id,
            "would_apply": False,
        }
    validation = readiness.validation
    return {
        "readiness_status": "ready_but_denied" if validation.ok else "blocked",
        **_instruction_boundary_payload(arguments),
        "operation_id": "",
        "eta_seconds": None,
        "validation_ok": validation.ok,
        "validation_errors": validation.errors,
        "normalized_paths": validation.normalized_paths,
        "safety_checkpoint_id": validation.summary.safety_checkpoint_id,
        "would_apply": False,
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items = cast("list[object]", value)
    return [str(item) for item in items if str(item)]


def _instruction_boundary_payload(arguments: dict[str, object]) -> dict[str, object]:
    free_text_fields = [key for key in ("text", "memory_text", "instruction") if key in arguments]
    return {
        "instruction_boundary": "typed_arguments_only",
        "ignored_free_text_fields": free_text_fields,
    }
# === ANCHOR: MCP_DENIED_HANDLERS_END ===
