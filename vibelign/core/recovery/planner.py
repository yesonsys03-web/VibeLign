# === ANCHOR: RECOVERY_PLANNER_START ===
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from vibelign.core.patch_suggester import suggest_recovery_level2_patch

from .intent_zone import build_intent_zone
from .models import DriftCandidate, DriftCircuitBreakerState, RecoveryOption, RecoveryPlan, RecoverySignalSet


_DRIFT_ACCURACY_MIN_WINDOW = 20
_DRIFT_ACCURACY_THRESHOLD = 0.80


# === ANCHOR: RECOVERY_PLANNER__BUILD_RECOVERY_PLAN_START ===
def build_recovery_plan(
    signals: RecoverySignalSet,
    *,
    project_root: Path | None = None,
    recovery_request: str = "",
) -> RecoveryPlan:
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

    options = _build_options(changed_paths, drift_candidates, signals, project_root, recovery_request)
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
    project_root: Path | None,
    recovery_request: str,
) -> list[RecoveryOption]:
    if not changed_paths and not signals.guard_has_failures:
        return [
            RecoveryOption(
                option_id=_new_id("opt"),
                level=0,
                label="복구할 내용 없음 — 변경된 파일이나 실패한 검사 결과가 없습니다.",
            )
        ]
    label = "1단계: 변경 내용 확인 — `vib explain`로 무엇이 바뀌었는지 확인하세요."
    if signals.explain_summary:
        label = f"최근 변경 설명 확인 — {signals.explain_summary}"
    options = [
        RecoveryOption(
            option_id=_new_id("opt"),
            level=1,
            label=label,
            affected_paths=changed_paths,
        )
    ]
    if signals.guard_has_failures:
        guard_label = "문제만 고치기 — 현재 작업은 유지하고 guard/test/build 실패를 고칩니다."
        if signals.guard_summary:
            guard_label = f"검사 실패 고치기 — {signals.guard_summary}"
        level2_target = _recovery_level2_target(project_root, recovery_request or signals.guard_summary)
        if level2_target:
            guard_label = f"{guard_label} 추천 수정 파일: {level2_target}."
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
                label="2단계: 낯선 파일 확인 — 아래 파일을 `vib explain <파일경로>` 또는 에디터로 열어 확인하세요.",
                affected_paths=[candidate.path for candidate in drift_candidates],
                blocked_reason="복원 전에 사용자 확인 필요",
            )
        )
    if signals.safe_checkpoint_candidate is not None and len(options) < 3:
        options.append(
            RecoveryOption(
                option_id=_new_id("opt"),
                level=3,
                label="3단계: 복원 미리보기 — 되돌릴 파일이 정해지면 `vib recover --file <파일경로>`를 실행하세요.",
                affected_paths=changed_paths,
                requires_sandwich=True,
                blocked_reason="복원 적용 기능은 아직 꺼져 있어 미리보기만 가능합니다",
            )
        )
    return options[:3]


def _recovery_level2_target(project_root: Path | None, recovery_request: str) -> str:
    if project_root is None or not recovery_request.strip():
        return ""
    suggestion = suggest_recovery_level2_patch(project_root, recovery_request)
    if suggestion.target_file == "[소스 파일 없음]":
        return ""
    return suggestion.target_file


def _summary_for(
    changed_paths: list[str],
    drift_candidates: list[DriftCandidate],
    signals: RecoverySignalSet,
    circuit_breaker_state: DriftCircuitBreakerState,
) -> str:
    if not changed_paths and not signals.guard_has_failures:
        return "변경된 파일이나 실패한 검사 결과가 없어 복구 작업이 필요하지 않습니다."
    details = [f"변경/새 파일 {len(changed_paths)}개 감지됨"]
    if drift_candidates:
        details.append(f"검토가 필요한 파일 {len(drift_candidates)}개")
    if circuit_breaker_state == "degraded":
        details.append("파일 분류 정확도가 낮아 검토 대상 표시를 잠시 껐습니다")
    if signals.safe_checkpoint_candidate is None:
        details.append("되돌릴 안전 체크포인트가 없습니다")
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
