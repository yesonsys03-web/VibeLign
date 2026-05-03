# === ANCHOR: RECOVERY_APPLY_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from vibelign.core.feature_flags import is_enabled
from vibelign.core.memory.audit import (
    AuditPathsCount,
    append_memory_audit_event,
    build_memory_audit_event,
    memory_audit_path,
)

from .locks import acquire_recovery_lock, read_recovery_lock, recovery_lock_path, release_recovery_lock
from .path import PathSafetyError, normalize_recovery_path


_VERIFICATION_RECOMMENDATIONS = [
    "Run targeted tests for recovered files.",
    "Run vib guard --strict before checkpointing recovery results.",
]


class RestoreFilesFunc(Protocol):
    def __call__(self, root: Path, checkpoint_id: str, relative_paths: list[str], /) -> int: ...


@dataclass(frozen=True)
class RecoveryApplyRequest:
    checkpoint_id: str
    sandwich_checkpoint_id: str
    paths: list[str] = field(default_factory=list)
    preview_paths: list[str] = field(default_factory=list)
    confirmation: str = ""
    apply: bool = False
    feature_enabled: bool = False


@dataclass(frozen=True)
class RecoveryCheckpointSandwichPrecondition:
    before_checkpoint_id: str
    safety_checkpoint_id: str
    ready: bool
    metadata_only: bool = True
    would_create_checkpoint: bool = False


@dataclass(frozen=True)
class RecoveryExplicitConfirmationPrecondition:
    expected_confirmation: str
    provided_confirmation: str
    ready: bool
    metadata_only: bool = True


@dataclass(frozen=True)
class RecoveryProjectLockPrecondition:
    lock_path: str
    ready: bool
    metadata_only: bool = True
    would_acquire_lock: bool = False
    active_lock_id: str = ""


@dataclass(frozen=True)
class RecoveryPathMatchPrecondition:
    preview_paths: list[str]
    apply_paths: list[str]
    ready: bool
    requires_reconfirmation: bool
    metadata_only: bool = True


@dataclass(frozen=True)
class RecoveryApplySummary:
    changed_files_count: int
    safety_checkpoint_id: str
    changed_files: list[str] = field(default_factory=list)
    verification_recommendations: list[str] = field(default_factory=lambda: list(_VERIFICATION_RECOMMENDATIONS))
    metadata_only: bool = True


@dataclass(frozen=True)
class RecoveryApplyFeatureGate:
    feature_name: str = "recovery_apply"
    enabled: bool = False
    blocked_reason: str | None = "Phase 5 recovery apply feature flag is disabled"
    metadata_only: bool = True


@dataclass(frozen=True)
class RecoveryApplyValidation:
    ok: bool
    normalized_paths: list[str]
    errors: list[str]
    sandwich_precondition: RecoveryCheckpointSandwichPrecondition
    confirmation_precondition: RecoveryExplicitConfirmationPrecondition
    lock_precondition: RecoveryProjectLockPrecondition
    path_match_precondition: RecoveryPathMatchPrecondition
    summary: RecoveryApplySummary
    feature_gate: RecoveryApplyFeatureGate
    metadata_only: bool = True
    would_apply: bool = False


@dataclass(frozen=True)
class RecoveryApplyReadiness:
    ok: bool
    busy: bool
    errors: list[str]
    validation: RecoveryApplyValidation
    lock_precondition: RecoveryProjectLockPrecondition
    operation_id: str = ""
    eta_seconds: int | None = None
    metadata_only: bool = True
    would_apply: bool = False


@dataclass(frozen=True)
class RecoveryApplyResult:
    ok: bool
    busy: bool
    errors: list[str]
    changed_files_count: int
    changed_files: list[str]
    safety_checkpoint_id: str
    operation_id: str = ""
    eta_seconds: int | None = None
    metadata_only: bool = False
    would_apply: bool = False


def validate_recovery_apply_request(project_root: Path, request: RecoveryApplyRequest) -> RecoveryApplyValidation:
    errors: list[str] = []
    normalized_paths: list[str] = []
    normalized_preview_paths: list[str] = []
    before_checkpoint_id = request.checkpoint_id.strip()
    safety_checkpoint_id = request.sandwich_checkpoint_id.strip()
    expected_confirmation = f"APPLY {before_checkpoint_id}" if before_checkpoint_id else ""
    provided_confirmation = request.confirmation.strip()
    sandwich_precondition = RecoveryCheckpointSandwichPrecondition(
        before_checkpoint_id=before_checkpoint_id,
        safety_checkpoint_id=safety_checkpoint_id,
        ready=bool(before_checkpoint_id and safety_checkpoint_id),
        metadata_only=True,
        would_create_checkpoint=False,
    )

    confirmation_precondition = RecoveryExplicitConfirmationPrecondition(
        expected_confirmation=expected_confirmation,
        provided_confirmation=provided_confirmation,
        ready=bool(expected_confirmation and provided_confirmation == expected_confirmation),
        metadata_only=True,
    )
    lock_precondition = RecoveryProjectLockPrecondition(
        lock_path=recovery_lock_path(project_root).relative_to(project_root).as_posix(),
        ready=False,
        metadata_only=True,
        would_acquire_lock=False,
    )
    feature_enabled = is_enabled("RECOVERY_APPLY")
    feature_gate = RecoveryApplyFeatureGate(
        feature_name="recovery_apply",
        enabled=feature_enabled,
        blocked_reason=None if feature_enabled else "Phase 5 recovery apply feature flag is disabled",
        metadata_only=True,
    )

    if request.apply and not feature_gate.enabled:
        errors.append("apply execution requires enabled recovery_apply feature flag")
    if not feature_gate.enabled and feature_gate.blocked_reason is not None:
        errors.append(feature_gate.blocked_reason)
    if not before_checkpoint_id:
        errors.append("checkpoint_id is required before recovery apply")
    if not safety_checkpoint_id:
        errors.append("sandwich_checkpoint_id is required before recovery apply")
    if not confirmation_precondition.ready:
        errors.append(f"explicit confirmation must match {expected_confirmation or 'APPLY <checkpoint_id>'}")
    if not request.paths:
        errors.append("at least one recovery path is required")
    if request.apply and not request.preview_paths:
        errors.append("preview_paths are required before recovery apply")

    for raw_preview_path in request.preview_paths:
        try:
            normalized_preview = normalize_recovery_path(project_root, raw_preview_path)
        except PathSafetyError as exc:
            errors.append(f"{_safe_error_path(raw_preview_path)}: {exc}")
            continue
        normalized_preview_paths.append(normalized_preview.relative_path)

    for raw_path in request.paths:
        try:
            normalized = normalize_recovery_path(project_root, raw_path)
        except PathSafetyError as exc:
            errors.append(f"{_safe_error_path(raw_path)}: {exc}")
            continue
        normalized_paths.append(normalized.relative_path)

    path_match_precondition = _build_path_match_precondition(normalized_preview_paths, normalized_paths)
    if not path_match_precondition.ready:
        errors.append("apply paths differ from preview paths; reconfirmation is required")
    summary = RecoveryApplySummary(
        changed_files_count=0,
        safety_checkpoint_id=safety_checkpoint_id,
        changed_files=[],
        verification_recommendations=list(_VERIFICATION_RECOMMENDATIONS),
        metadata_only=True,
    )

    if errors:
        normalized_paths = []

    return RecoveryApplyValidation(
        ok=not errors,
        normalized_paths=normalized_paths,
        errors=errors,
        sandwich_precondition=sandwich_precondition,
        confirmation_precondition=confirmation_precondition,
        lock_precondition=lock_precondition,
        path_match_precondition=path_match_precondition,
        summary=summary,
        feature_gate=feature_gate,
        metadata_only=True,
        would_apply=False,
    )


def execute_recovery_apply(
    project_root: Path,
    request: RecoveryApplyRequest,
    *,
    owner_tool: str = "vib-cli",
    restore_files_func: RestoreFilesFunc | None = None,
    now: str | None = None,
) -> RecoveryApplyResult:
    readiness = check_recovery_apply_readiness(project_root, request, now=now)
    if readiness.busy:
        return RecoveryApplyResult(
            ok=False,
            busy=True,
            errors=readiness.errors,
            changed_files_count=0,
            changed_files=[],
            safety_checkpoint_id=readiness.validation.summary.safety_checkpoint_id,
            operation_id=readiness.operation_id,
            eta_seconds=readiness.eta_seconds,
            metadata_only=False,
            would_apply=False,
        )
    if not request.apply:
        return _blocked_apply_result(readiness.validation, [*readiness.errors, "apply=True is required"])
    if not readiness.ok:
        _append_recovery_apply_audit(project_root, readiness.validation.normalized_paths, readiness.validation.summary.safety_checkpoint_id, "blocked", owner_tool)
        return _blocked_apply_result(readiness.validation, readiness.errors)

    lock = acquire_recovery_lock(project_root, owner_tool=owner_tool, reason="recovery apply", now=now)
    if lock.busy:
        return RecoveryApplyResult(
            ok=False,
            busy=True,
            errors=["recovery apply is busy"],
            changed_files_count=0,
            changed_files=[],
            safety_checkpoint_id=readiness.validation.summary.safety_checkpoint_id,
            operation_id=lock.operation_id,
            eta_seconds=lock.eta_seconds,
            metadata_only=False,
            would_apply=False,
        )

    restore = restore_files_func or _restore_files
    try:
        restored_count = restore(project_root, request.checkpoint_id.strip(), readiness.validation.normalized_paths)
    except Exception as exc:
        _append_recovery_apply_audit(project_root, readiness.validation.normalized_paths, readiness.validation.summary.safety_checkpoint_id, "error", owner_tool)
        return _blocked_apply_result(readiness.validation, [str(exc)])
    finally:
        _ = release_recovery_lock(project_root, lock_id=lock.state.lock_id)

    _append_recovery_apply_audit(project_root, readiness.validation.normalized_paths, readiness.validation.summary.safety_checkpoint_id, "success", owner_tool)
    return RecoveryApplyResult(
        ok=True,
        busy=False,
        errors=[],
        changed_files_count=restored_count,
        changed_files=readiness.validation.normalized_paths,
        safety_checkpoint_id=readiness.validation.summary.safety_checkpoint_id,
        operation_id=lock.state.lock_id,
        eta_seconds=None,
        metadata_only=False,
        would_apply=True,
    )


def check_recovery_apply_readiness(
    project_root: Path,
    request: RecoveryApplyRequest,
    *,
    now: str | None = None,
) -> RecoveryApplyReadiness:
    validation = validate_recovery_apply_request(project_root, request)
    lock_status = read_recovery_lock(project_root, now=now)
    if lock_status.active:
        active_lock_id = lock_status.state.lock_id
        lock_precondition = RecoveryProjectLockPrecondition(
            lock_path=recovery_lock_path(project_root).relative_to(project_root).as_posix(),
            ready=False,
            metadata_only=True,
            would_acquire_lock=False,
            active_lock_id=active_lock_id,
        )
        return RecoveryApplyReadiness(
            ok=False,
            busy=True,
            errors=[*validation.errors, "recovery apply is busy"],
            validation=validation,
            lock_precondition=lock_precondition,
            operation_id=active_lock_id,
            eta_seconds=lock_status.eta_seconds,
            metadata_only=True,
            would_apply=False,
        )

    lock_precondition = RecoveryProjectLockPrecondition(
        lock_path=recovery_lock_path(project_root).relative_to(project_root).as_posix(),
        ready=True,
        metadata_only=True,
        would_acquire_lock=False,
        active_lock_id="",
    )
    return RecoveryApplyReadiness(
        ok=validation.ok,
        busy=False,
        errors=validation.errors,
        validation=validation,
        lock_precondition=lock_precondition,
        operation_id="",
        eta_seconds=None,
        metadata_only=True,
        would_apply=False,
    )


def _restore_files(root: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
    from vibelign.core.checkpoint_engine.router import restore_files

    return restore_files(root, checkpoint_id, relative_paths)


def _safe_error_path(raw_path: str) -> str:
    if raw_path.startswith("/") or raw_path.startswith("\\\\") or (len(raw_path) > 2 and raw_path[1] == ":"):
        return "<absolute-path>"
    return raw_path


def _blocked_apply_result(validation: RecoveryApplyValidation, errors: list[str]) -> RecoveryApplyResult:
    return RecoveryApplyResult(
        ok=False,
        busy=False,
        errors=errors,
        changed_files_count=0,
        changed_files=[],
        safety_checkpoint_id=validation.summary.safety_checkpoint_id,
        operation_id="",
        eta_seconds=None,
        metadata_only=False,
        would_apply=False,
    )


def _append_recovery_apply_audit(
    project_root: Path,
    paths: list[str],
    sandwich_checkpoint_id: str,
    result: str,
    owner_tool: str,
) -> None:
    audit_result = "success" if result == "success" else "blocked" if result == "blocked" else "error"
    append_memory_audit_event(
        memory_audit_path(project_root),
        build_memory_audit_event(
            project_root,
            event="recovery_apply",
            tool=owner_tool,
            paths_count=AuditPathsCount(in_zone=len(paths), drift=0, total=len(paths)),
            result=audit_result,
            sandwich_checkpoint_id=sandwich_checkpoint_id,
        ),
    )


def _build_path_match_precondition(preview_paths: list[str], apply_paths: list[str]) -> RecoveryPathMatchPrecondition:
    preview_set = set(preview_paths)
    apply_set = set(apply_paths)
    requires_reconfirmation = bool(preview_paths) and preview_set != apply_set
    return RecoveryPathMatchPrecondition(
        preview_paths=preview_paths,
        apply_paths=apply_paths,
        ready=not requires_reconfirmation,
        requires_reconfirmation=requires_reconfirmation,
        metadata_only=True,
    )
# === ANCHOR: RECOVERY_APPLY_END ===
