import os
from pathlib import Path

from vibelign.core.recovery.apply import RecoveryApplyRequest, validate_recovery_apply_request


def test_validate_recovery_apply_request_blocks_default_off_feature_gate(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_123",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src\\app.py"],
        preview_paths=["src/app.py"],
        confirmation="APPLY ckpt_123",
        apply=False,
    )

    result = validate_recovery_apply_request(root, request)

    assert result.ok is False
    assert result.normalized_paths == []
    assert result.metadata_only is True
    assert result.would_apply is False
    assert result.sandwich_precondition.metadata_only is True
    assert result.sandwich_precondition.ready is True
    assert result.sandwich_precondition.before_checkpoint_id == "ckpt_123"
    assert result.sandwich_precondition.safety_checkpoint_id == "ckpt_safety"
    assert result.sandwich_precondition.would_create_checkpoint is False
    assert result.confirmation_precondition.metadata_only is True
    assert result.confirmation_precondition.ready is True
    assert result.confirmation_precondition.expected_confirmation == "APPLY ckpt_123"
    assert result.confirmation_precondition.provided_confirmation == "APPLY ckpt_123"
    assert result.lock_precondition.metadata_only is True
    assert result.lock_precondition.ready is False
    assert result.lock_precondition.lock_path == ".vibelign/recovery/recovery.lock.json"
    assert result.lock_precondition.would_acquire_lock is False
    assert result.path_match_precondition.metadata_only is True
    assert result.path_match_precondition.ready is True
    assert result.path_match_precondition.preview_paths == ["src/app.py"]
    assert result.path_match_precondition.apply_paths == ["src/app.py"]
    assert result.path_match_precondition.requires_reconfirmation is False
    assert result.summary.metadata_only is True
    assert result.summary.changed_files_count == 0
    assert result.summary.safety_checkpoint_id == "ckpt_safety"
    assert result.summary.changed_files == []
    assert result.summary.verification_recommendations == [
        "Run targeted tests for recovered files.",
        "Run vib guard --strict before checkpointing recovery results.",
    ]
    assert result.feature_gate.metadata_only is True
    assert result.feature_gate.feature_name == "recovery_apply"
    assert result.feature_gate.enabled is False
    assert result.feature_gate.blocked_reason == "Phase 5 recovery apply feature flag is disabled"
    assert "Phase 5 recovery apply feature flag is disabled" in result.errors
    assert result.ok is False
    assert result.normalized_paths == []


def test_validate_recovery_apply_request_can_model_enabled_feature_gate_without_applying(tmp_path: Path) -> None:
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
        apply=False,
        feature_enabled=True,
    )

    try:
        result = validate_recovery_apply_request(root, request)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.feature_gate.metadata_only is True
    assert result.feature_gate.enabled is True
    assert result.feature_gate.blocked_reason is None
    assert result.ok is True
    assert result.normalized_paths == ["src/app.py"]
    assert result.would_apply is False
    assert not (root / ".vibelign" / "recovery" / "recovery.lock.json").exists()
    assert result.errors == []
    assert not (root / ".vibelign" / "recovery" / "recovery.lock.json").exists()


def test_validate_recovery_apply_request_requires_preview_paths_for_apply(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_123",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py"],
        preview_paths=[],
        confirmation="APPLY ckpt_123",
        apply=True,
        feature_enabled=True,
    )

    try:
        result = validate_recovery_apply_request(root, request)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is False
    assert result.normalized_paths == []
    assert "preview_paths are required before recovery apply" in result.errors


def test_validate_recovery_apply_request_reads_recovery_apply_env_flag(tmp_path: Path) -> None:
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
        apply=False,
    )

    try:
        result = validate_recovery_apply_request(root, request)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.feature_gate.enabled is True
    assert result.feature_gate.blocked_reason is None
    assert result.ok is True
    assert result.would_apply is False
    assert not (root / ".vibelign" / "recovery" / "recovery.lock.json").exists()


def test_validate_recovery_apply_request_rejects_apply_and_unsafe_paths(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_123",
        sandwich_checkpoint_id="",
        paths=["../secret.py", "node_modules/pkg/index.js"],
        preview_paths=["src/app.py"],
        confirmation="wrong",
        apply=True,
    )

    result = validate_recovery_apply_request(root, request)

    assert result.ok is False
    assert result.normalized_paths == []
    assert result.metadata_only is True
    assert result.would_apply is False
    assert result.sandwich_precondition.metadata_only is True
    assert result.sandwich_precondition.ready is False
    assert result.sandwich_precondition.would_create_checkpoint is False
    assert result.confirmation_precondition.metadata_only is True
    assert result.confirmation_precondition.ready is False
    assert result.confirmation_precondition.expected_confirmation == "APPLY ckpt_123"
    assert result.confirmation_precondition.provided_confirmation == "wrong"
    assert result.lock_precondition.metadata_only is True
    assert result.lock_precondition.ready is False
    assert result.lock_precondition.lock_path == ".vibelign/recovery/recovery.lock.json"
    assert result.lock_precondition.would_acquire_lock is False
    assert result.path_match_precondition.metadata_only is True
    assert result.path_match_precondition.ready is False
    assert result.path_match_precondition.preview_paths == ["src/app.py"]
    assert result.path_match_precondition.apply_paths == []
    assert result.path_match_precondition.requires_reconfirmation is True
    assert result.summary.metadata_only is True
    assert result.summary.changed_files_count == 0
    assert result.summary.safety_checkpoint_id == ""
    assert result.summary.changed_files == []
    assert "apply execution requires enabled recovery_apply feature flag" in result.errors
    assert "explicit confirmation must match APPLY ckpt_123" in result.errors
    assert "sandwich_checkpoint_id is required before recovery apply" in result.errors
    assert any("../secret.py" in error for error in result.errors)
    assert any("node_modules/pkg/index.js" in error for error in result.errors)


def test_validate_recovery_apply_request_redacts_absolute_path_errors(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = root.mkdir()
    outside = tmp_path / "secret.py"
    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_123",
        sandwich_checkpoint_id="ckpt_safety",
        paths=[str(outside)],
        preview_paths=[str(outside)],
        confirmation="APPLY ckpt_123",
        feature_enabled=True,
    )

    try:
        result = validate_recovery_apply_request(root, request)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    errors = "\n".join(result.errors)
    assert str(outside) not in errors
    assert "<absolute-path>" in errors


def test_validate_recovery_apply_request_requires_reconfirmation_for_preview_path_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    _ = (root / "src" / "other.py").write_text("print('other')\n", encoding="utf-8")
    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_123",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py"],
        preview_paths=["src/other.py"],
        confirmation="APPLY ckpt_123",
        apply=False,
    )

    result = validate_recovery_apply_request(root, request)

    assert result.ok is False
    assert result.normalized_paths == []
    assert result.path_match_precondition.metadata_only is True
    assert result.path_match_precondition.ready is False
    assert result.path_match_precondition.preview_paths == ["src/other.py"]
    assert result.path_match_precondition.apply_paths == ["src/app.py"]
    assert result.path_match_precondition.requires_reconfirmation is True
    assert result.summary.metadata_only is True
    assert result.summary.changed_files_count == 0
    assert result.summary.safety_checkpoint_id == "ckpt_safety"
    assert result.summary.changed_files == []
    assert "apply paths differ from preview paths; reconfirmation is required" in result.errors
