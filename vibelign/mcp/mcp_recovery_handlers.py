from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from vibelign.core.memory.audit import (
    append_memory_audit_event,
    build_memory_audit_event,
    memory_audit_path,
)
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
    _ = arguments
    plan = build_recovery_plan(collect_basic_signals(root))
    append_memory_audit_event(
        memory_audit_path(root),
        build_memory_audit_event(
            root,
            event="recovery_preview",
            tool="mcp",
            result="success",
        ),
    )
    payload: dict[str, object] = {
        "ok": True,
        "read_only": True,
        "provenance": "recovery_planner_preview",
        "plan": _plan_to_payload(plan),
    }
    return _text(text_content, json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _plan_to_payload(plan: RecoveryPlan) -> dict[str, object]:
    return {
        "plan_id": plan.plan_id,
        "mode": plan.mode,
        "level": plan.level,
        "summary": plan.summary,
        "no_files_modified": plan.no_files_modified,
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
