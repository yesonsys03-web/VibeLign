from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.memory.audit import (
    AuditPathsCount,
    append_memory_audit_event,
    build_memory_audit_event,
    memory_audit_path,
)
from vibelign.core.memory.aggregator import aggregate_p0_occurrences, p0_occurrence_summary_to_dict
from vibelign.core.memory.retention import apply_memory_audit_retention
from vibelign.core.recovery.models import (
    DriftCandidate,
    IntentZoneEntry,
    RecoveryOption,
    RecoveryPlan,
    SafeCheckpointCandidate,
)
from vibelign.core.recovery.planner import build_recovery_plan
from vibelign.core.recovery.signals import collect_basic_signals


class TextContentFactory(Protocol):
    def __call__(self, *, type: str, text: str) -> object: ...


def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]


def handle_recovery_preview(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    recovery_request = str(arguments.get("request", ""))
    plan = build_recovery_plan(collect_basic_signals(root), project_root=root, recovery_request=recovery_request)
    append_memory_audit_event(
        memory_audit_path(root),
        build_memory_audit_event(
            root,
            event="recovery_preview",
            tool="mcp",
            paths_count=_audit_paths_count(plan),
            result="success",
        ),
    )
    _ = apply_memory_audit_retention(root, active_window_start=_release_window_start())
    payload: dict[str, object] = {
        "ok": True,
        "read_only": True,
        "provenance": "recovery_planner_preview",
        "plan": _plan_to_payload(plan),
        "p0_summaries": [
            p0_occurrence_summary_to_dict(summary)
            for summary in aggregate_p0_occurrences(
                root,
                window_start=_release_window_start(),
                window_end=_utc_now(),
            )
        ],
    }
    return _text(text_content, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def handle_recovery_apply(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.recovery.apply import RecoveryApplyRequest, execute_recovery_apply

    result = execute_recovery_apply(
        root,
        RecoveryApplyRequest(
            checkpoint_id=str(arguments.get("checkpoint_id", "")),
            sandwich_checkpoint_id=str(arguments.get("sandwich_checkpoint_id", "")),
            paths=_string_list(arguments.get("paths")),
            preview_paths=_string_list(arguments.get("preview_paths")),
            confirmation=str(arguments.get("confirmation", "")),
            apply=arguments.get("apply") is True,
        ),
        owner_tool=str(arguments.get("tool", "mcp")) or "mcp",
    )
    payload: dict[str, object] = {
        "ok": result.ok,
        "capability": "recovery_apply",
        "busy": result.busy,
        "errors": result.errors,
        "changed_files_count": result.changed_files_count,
        "changed_files": result.changed_files,
        "safety_checkpoint_id": result.safety_checkpoint_id,
        "operation_id": result.operation_id,
        "eta_seconds": result.eta_seconds,
        "would_apply": result.would_apply,
    }
    return _text(text_content, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items = cast(list[object], value)
    return [str(item) for item in items if str(item)]


def _audit_paths_count(plan: RecoveryPlan) -> AuditPathsCount:
    in_zone = len(plan.intent_zone)
    drift = len(plan.drift_candidates)
    return AuditPathsCount(in_zone=in_zone, drift=drift, total=in_zone + drift)


def _plan_to_payload(plan: RecoveryPlan) -> dict[str, object]:
    return {
        "plan_id": plan.plan_id,
        "mode": plan.mode,
        "level": plan.level,
        "summary": plan.summary,
        "no_files_modified": plan.no_files_modified,
        "circuit_breaker_state": plan.circuit_breaker_state,
        "intent_zone": [_intent_zone_to_payload(item) for item in plan.intent_zone],
        "drift_candidates": [_drift_candidate_to_payload(item) for item in plan.drift_candidates],
        "options": [_option_to_payload(item) for item in plan.options],
        "safe_checkpoint_candidate": _checkpoint_to_payload(plan.safe_checkpoint_candidate),
    }


def _intent_zone_to_payload(item: IntentZoneEntry) -> dict[str, object]:
    return {"path": item.path, "source": item.source, "reason": item.reason}


def _drift_candidate_to_payload(item: DriftCandidate) -> dict[str, object]:
    return {
        "path": item.path,
        "why_outside_zone": item.why_outside_zone,
        "suggested_action": item.suggested_action,
        "requires_user_review": item.requires_user_review,
    }


def _option_to_payload(item: RecoveryOption) -> dict[str, object]:
    return {
        "option_id": item.option_id,
        "level": item.level,
        "label": item.label,
        "affected_paths": item.affected_paths,
        "estimated_impact": item.estimated_impact,
        "requires_sandwich": item.requires_sandwich,
        "requires_lock": item.requires_lock,
        "blocked_reason": item.blocked_reason,
    }


def _checkpoint_to_payload(item: SafeCheckpointCandidate | None) -> dict[str, object] | None:
    if item is None:
        return None
    return {
        "checkpoint_id": item.checkpoint_id,
        "created_at": item.created_at,
        "message": item.message,
        "metadata_complete": item.metadata_complete,
        "preview_available": item.preview_available,
        "predates_change": item.predates_change,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _release_window_start() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=90)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
