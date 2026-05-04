from vibelign.core.recovery.models import RecoverySignalSet, SafeCheckpointCandidate
from vibelign.core.recovery.planner import build_recovery_plan


def test_no_checkpoint_blocks_full_rollback_recommendation() -> None:
    plan = build_recovery_plan(
        RecoverySignalSet(changed_paths=["src/auth.py"], safe_checkpoint_candidate=None)
    )

    assert plan.mode == "read_only"
    assert plan.no_files_modified is True
    assert plan.safe_checkpoint_candidate is None
    assert all(option.level < 3 for option in plan.options)


def test_drift_candidate_is_review_only() -> None:
    plan = build_recovery_plan(
        RecoverySignalSet(
            changed_paths=["src/ui.py", "src/auth.py"],
            explicit_relevant_paths=["src/ui.py"],
        )
    )

    assert [candidate.path for candidate in plan.drift_candidates] == ["src/auth.py"]
    assert any(option.blocked_reason == "복원 전에 사용자 확인 필요" for option in plan.options)


def test_valid_checkpoint_adds_preview_only_option() -> None:
    plan = build_recovery_plan(
        RecoverySignalSet(
            changed_paths=["src/auth.py"],
            safe_checkpoint_candidate=SafeCheckpointCandidate(
                checkpoint_id="cp_1",
                created_at="2026-05-02T00:00:00Z",
                message="before work",
                metadata_complete=True,
                preview_available=True,
                predates_change=True,
            ),
        )
    )

    assert len(plan.options) <= 3
    assert any(option.level == 3 for option in plan.options)
    assert all(option.level < 4 for option in plan.options)


def test_drift_accuracy_circuit_breaker_degrades_to_diff_aware_mode() -> None:
    plan = build_recovery_plan(
        RecoverySignalSet(
            changed_paths=["src/ui.py", "src/auth.py"],
            explicit_relevant_paths=["src/ui.py"],
            drift_accuracy_window_size=20,
            drift_accuracy_confirmed_correct=15,
            drift_accuracy_confirmed_incorrect=5,
        )
    )

    assert plan.circuit_breaker_state == "degraded"
    assert plan.drift_candidates == []
    assert "파일 분류 정확도가 낮아" in plan.summary
    assert all("drift" not in option.label.lower() for option in plan.options)


def test_drift_accuracy_circuit_breaker_stays_active_above_threshold() -> None:
    plan = build_recovery_plan(
        RecoverySignalSet(
            changed_paths=["src/ui.py", "src/auth.py"],
            explicit_relevant_paths=["src/ui.py"],
            drift_accuracy_window_size=20,
            drift_accuracy_confirmed_correct=16,
            drift_accuracy_confirmed_incorrect=4,
        )
    )

    assert plan.circuit_breaker_state == "active"
    assert [candidate.path for candidate in plan.drift_candidates] == ["src/auth.py"]


def test_level2_recovery_option_includes_deterministic_patch_target(tmp_path) -> None:
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "auth.py").write_text("def login():\n    return False\n", encoding="utf-8")
    _ = (root / "src" / "ui.py").write_text("def render():\n    return 'ok'\n", encoding="utf-8")

    plan = build_recovery_plan(
        RecoverySignalSet(
            changed_paths=["src/auth.py"],
            guard_has_failures=True,
            guard_summary="login fails",
        ),
        project_root=root,
        recovery_request="fix login failure",
    )
    level2_option = next(option for option in plan.options if option.level == 2)

    assert "추천 수정 파일: src/auth.py" in level2_option.label
