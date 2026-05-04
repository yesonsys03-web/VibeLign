# === ANCHOR: VIB_RECOVER_CMD_START ===
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from vibelign.core.memory.audit import AuditPathsCount
from vibelign.core.memory.audit import append_memory_audit_event
from vibelign.core.memory.audit import build_memory_audit_event
from vibelign.core.memory.audit import memory_audit_path
from vibelign.core.memory.aggregator import aggregate_p0_occurrences, p0_occurrence_summary_to_dict
from vibelign.core.memory.retention import apply_memory_audit_retention
from vibelign.core.project_root import resolve_project_root
from vibelign.core.recovery.models import RecoveryPlan
from vibelign.core.recovery.apply import RecoveryApplyRequest, execute_recovery_apply
from vibelign.core.recovery.path import PathSafetyError, normalize_recovery_path
from vibelign.core.recovery.planner import build_recovery_plan
from vibelign.core.recovery.render import render_text_plan
from vibelign.core.recovery.signals import collect_basic_signals
from vibelign.core.schema_contracts import validate_recovery_plan_payload
from vibelign.terminal_render import cli_print

print = cli_print

_RECOVER_HELP = "Recovery Advisor is read-only. Run: vib recover --explain, vib recover --preview, or vib recover --file <path>"


class RecoverArgs(Protocol):
    explain: bool
    preview: bool
    file: str | None
    json: bool
    apply: bool
    checkpoint_id: str
    sandwich_checkpoint_id: str
    confirmation: str


# === ANCHOR: VIB_RECOVER_CMD__RUN_VIB_RECOVER_START ===
def run_vib_recover(args: RecoverArgs) -> None:
    file_target = args.file
    if not (args.explain or args.preview or file_target):
        print(_RECOVER_HELP)
        return

    project_root = resolve_project_root(Path.cwd())
    if args.apply:
        print(_run_file_apply(project_root, args))
        return

    signals = collect_basic_signals(project_root)
    plan = build_recovery_plan(signals, project_root=project_root, recovery_request=file_target or "")
    append_memory_audit_event(
        memory_audit_path(project_root),
        build_memory_audit_event(
            project_root,
            event="recovery_preview",
            tool="vib-cli",
            paths_count=_audit_paths_count(plan),
            result="success",
        ),
    )
    _ = apply_memory_audit_retention(project_root, active_window_start=_release_window_start())
    p0_summaries = [
        p0_occurrence_summary_to_dict(summary)
        for summary in aggregate_p0_occurrences(
            project_root,
            window_start=_release_window_start(),
            window_end=_utc_now(),
        )
    ]
    if args.json:
        payload = _plan_payload(plan)
        payload["p0_summaries"] = p0_summaries
        validate_recovery_plan_payload(payload)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    output = render_text_plan(plan)
    if file_target:
        output = f"{output}\n\n{_render_file_preview(project_root, file_target)}"
    print(output)
# === ANCHOR: VIB_RECOVER_CMD__RUN_VIB_RECOVER_END ===


def _render_file_preview(project_root: Path, file_target: str) -> str:
    try:
        normalized = normalize_recovery_path(
            project_root,
            file_target,
            trusted_local_cli=True,
        )
    except PathSafetyError as exc:
        return f"복원 미리보기 대상을 확인할 수 없습니다: {exc}"
    return (
        f"복원 미리보기 대상: {normalized.display_path}\n"
        "아직 파일은 되돌리지 않았습니다. 이 경로가 맞는지 확인하세요."
    )


def _run_file_apply(project_root: Path, args: RecoverArgs) -> str:
    file_target = args.file or ""
    result = execute_recovery_apply(
        project_root,
        RecoveryApplyRequest(
            checkpoint_id=args.checkpoint_id,
            sandwich_checkpoint_id=args.sandwich_checkpoint_id,
            paths=[file_target] if file_target else [],
            preview_paths=[file_target] if file_target else [],
            confirmation=args.confirmation,
            apply=True,
        ),
    )
    if not result.ok:
        errors = "; ".join(result.errors) or "recovery apply failed"
        return f"Recovery apply blocked\nNo files were modified.\nErrors: {errors}"
    return (
        "Recovery apply completed\n"
        f"changed files: {result.changed_files_count}\n"
        f"safety checkpoint: {result.safety_checkpoint_id}\n"
        f"operation: {result.operation_id}"
    )


def _audit_paths_count(plan: RecoveryPlan) -> AuditPathsCount:
    in_zone = len(plan.intent_zone)
    drift = len(plan.drift_candidates)
    return AuditPathsCount(in_zone=in_zone, drift=drift, total=in_zone + drift)


def _plan_payload(plan) -> dict[str, object]:
    return {
        "plan_id": plan.plan_id,
        "mode": plan.mode,
        "level": plan.level,
        "summary": plan.summary,
        "intent_zone": [item.__dict__ for item in plan.intent_zone],
        "drift_candidates": [item.__dict__ for item in plan.drift_candidates],
        "options": [item.__dict__ for item in plan.options],
        "safe_checkpoint_candidate": plan.safe_checkpoint_candidate.__dict__ if plan.safe_checkpoint_candidate else None,
        "no_files_modified": plan.no_files_modified,
        "circuit_breaker_state": plan.circuit_breaker_state,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _release_window_start() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=90)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# === ANCHOR: VIB_RECOVER_CMD_END ===
