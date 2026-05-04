from pathlib import Path
import os

from vibelign.core.recovery.apply import RecoveryApplyRequest, check_recovery_apply_readiness
from vibelign.core.recovery.locks import acquire_recovery_lock, recovery_lock_path


def test_check_recovery_apply_readiness_reports_busy_when_lock_is_active(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = root.mkdir()
    lock = acquire_recovery_lock(
        root,
        owner_tool="claude",
        reason="apply in progress",
        now="2026-05-03T10:00:00Z",
        ttl_seconds=60,
    )
    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_123",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py"],
        preview_paths=["src/app.py"],
        confirmation="APPLY ckpt_123",
    )

    try:
        result = check_recovery_apply_readiness(root, request, now="2026-05-03T10:00:10Z")
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is False
    assert result.busy is True
    assert result.operation_id == lock.state.lock_id
    assert result.eta_seconds == 50
    assert result.would_apply is False
    assert result.lock_precondition.ready is False
    assert result.lock_precondition.active_lock_id == lock.state.lock_id
    assert "recovery apply is busy" in result.errors
    assert recovery_lock_path(root).exists()


def test_check_recovery_apply_readiness_validates_when_no_active_lock(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_123",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py"],
        preview_paths=["src/app.py"],
        confirmation="APPLY ckpt_123",
    )

    try:
        result = check_recovery_apply_readiness(root, request, now="2026-05-03T10:00:00Z")
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is True
    assert result.busy is False
    assert result.operation_id == ""
    assert result.eta_seconds is None
    assert result.would_apply is False
    assert result.lock_precondition.ready is True
    assert result.lock_precondition.active_lock_id == ""
    assert not recovery_lock_path(root).exists()
