# === ANCHOR: RECOVERY_PLANNER_START ===
from __future__ import annotations

from uuid import uuid4

from .intent_zone import build_intent_zone
from .models import DriftCandidate, DriftCircuitBreakerState, RecoveryOption, RecoveryPlan, RecoverySignalSet


_DRIFT_ACCURACY_MIN_WINDOW = 20
_DRIFT_ACCURACY_THRESHOLD = 0.80


# === ANCHOR: RECOVERY_PLANNER__BUILD_RECOVERY_PLAN_START ===
def build_recovery_plan(signals: RecoverySignalSet) -> RecoveryPlan:
    changed_paths = [*signals.changed_paths, *signals.untracked_paths]
    circuit_breaker_state = _drift_circuit_breaker_state(signals)
    intent_zone, drift_candidates = build_intent_zone(
        explicit_relevant_paths=signals.explicit_relevant_paths,
        recent_patch_paths=signals.recent_patch_paths,
        changed_paths=changed_paths,
        project_map_categories=signals.project_map_categories,
        anchor_intents_by_path=signals.anchor_intents_by_path,
    )
    if circuit_breaker_state == "degraded":
        drift_candidates = []

    options = _build_options(changed_paths, drift_candidates, signals)
    level = options[0].level if options else 0
    summary = _summary_for(changed_paths, drift_candidates, signals, circuit_breaker_state)
    return RecoveryPlan(
        plan_id=_new_id("rec"),
        mode="read_only",
        level=level,
        summary=summary,
        intent_zone=intent_zone,
        drift_candidates=drift_candidates,
        options=options,
        safe_checkpoint_candidate=signals.safe_checkpoint_candidate,
        no_files_modified=True,
        circuit_breaker_state=circuit_breaker_state,
    )
# === ANCHOR: RECOVERY_PLANNER__BUILD_RECOVERY_PLAN_END ===


def _build_options(
    changed_paths: list[str],
    drift_candidates: list[DriftCandidate],
    signals: RecoverySignalSet,
) -> list[RecoveryOption]:
    if not changed_paths and not signals.guard_has_failures:
        return [
            RecoveryOption(
                option_id=_new_id("opt"),
                level=0,
                label="No-op recovery — no changed files or known guard failures were found.",
            )
        ]
    label = "Explain only — review changed files and risk signals before applying any restore."
    if signals.explain_summary:
        label = f"Explain only — review latest explain summary: {signals.explain_summary}"
    options = [
        RecoveryOption(
            option_id=_new_id("opt"),
            level=1,
            label=label,
            affected_paths=changed_paths,
        )
    ]
    if signals.guard_has_failures:
        guard_label = "Targeted repair — keep the work and fix guard/test/build failures."
        if signals.guard_summary:
            guard_label = f"Targeted repair — address guard summary: {signals.guard_summary}"
        options.append(
            RecoveryOption(
                option_id=_new_id("opt"),
                level=2,
                label=guard_label,
                affected_paths=changed_paths,
            )
        )
    if drift_candidates:
        options.append(
            RecoveryOption(
                option_id=_new_id("opt"),
                level=1,
                label="Review drift candidates — confirm whether out-of-zone files were intentional.",
                affected_paths=[candidate.path for candidate in drift_candidates],
                blocked_reason="user review required before any restore",
            )
        )
    if signals.safe_checkpoint_candidate is not None and len(options) < 3:
        options.append(
            RecoveryOption(
                option_id=_new_id("opt"),
                level=3,
                label="Partial restore preview — inspect selected files from the latest validated checkpoint before any apply.",
                affected_paths=changed_paths,
                requires_sandwich=True,
                blocked_reason="Phase 5 apply is not enabled; preview only",
            )
        )
    return options[:3]


def _summary_for(
    changed_paths: list[str],
    drift_candidates: list[DriftCandidate],
    signals: RecoverySignalSet,
    circuit_breaker_state: DriftCircuitBreakerState,
) -> str:
    if not changed_paths and not signals.guard_has_failures:
        return "No changed files or known guard failures were found; no recovery action is needed."
    details = [f"{len(changed_paths)} changed/untracked file(s) detected"]
    if drift_candidates:
        details.append(f"{len(drift_candidates)} drift candidate(s) require user review")
    if circuit_breaker_state == "degraded":
        details.append("drift labeling temporarily disabled — accuracy below threshold")
    if signals.safe_checkpoint_candidate is None:
        details.append("no safe checkpoint candidate is available for rollback")
    return "; ".join(details) + "."


def _drift_circuit_breaker_state(signals: RecoverySignalSet) -> DriftCircuitBreakerState:
    total = signals.drift_accuracy_confirmed_correct + signals.drift_accuracy_confirmed_incorrect
    if signals.drift_accuracy_window_size < _DRIFT_ACCURACY_MIN_WINDOW or total < _DRIFT_ACCURACY_MIN_WINDOW:
        return "active"
    accuracy = signals.drift_accuracy_confirmed_correct / total
    return "degraded" if accuracy < _DRIFT_ACCURACY_THRESHOLD else "active"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"

# === ANCHOR: RECOVERY_PLANNER_END ===
