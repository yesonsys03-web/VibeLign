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
    assert any(option.blocked_reason == "user review required before any restore" for option in plan.options)


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
