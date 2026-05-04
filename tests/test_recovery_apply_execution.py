import json
import os
from pathlib import Path
from typing import cast

from vibelign.core.memory.audit import memory_audit_path
from vibelign.core.recovery.apply import RecoveryApplyRequest, execute_recovery_apply
from vibelign.core.recovery.locks import (
    acquire_recovery_lock,
    read_recovery_lock,
    recovery_lock_path,
    release_recovery_lock,
)


def test_execute_recovery_apply_restores_selected_files_with_lock_and_audit(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("broken\n", encoding="utf-8")
    calls: list[tuple[str, list[str]]] = []

    def restore_files(root_path: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
        assert root_path == root
        calls.append((checkpoint_id, relative_paths))
        return len(relative_paths)

    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_before",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src\\app.py"],
        preview_paths=["src/app.py"],
        confirmation="APPLY ckpt_before",
        apply=True,
    )

    try:
        result = execute_recovery_apply(root, request, restore_files_func=restore_files)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is True
    assert result.would_apply is True
    assert result.metadata_only is False
    assert result.changed_files_count == 1
    assert result.changed_files == ["src/app.py"]
    assert result.safety_checkpoint_id == "ckpt_safety"
    assert calls == [("ckpt_before", ["src/app.py"])]
    assert not recovery_lock_path(root).exists()
    audit_line = memory_audit_path(root).read_text(encoding="utf-8").strip()
    audit_payload = cast(dict[str, object], json.loads(audit_line))
    assert audit_payload["event"] == "recovery_apply"
    assert audit_payload["result"] == "success"
    assert audit_payload["sandwich_checkpoint_id"] == "ckpt_safety"
    assert audit_payload["paths_count"] == {"drift": 0, "in_zone": 1, "total": 1}


def test_execute_recovery_apply_reports_busy_without_restoring(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = root.mkdir()
    active_lock = acquire_recovery_lock(
        root,
        owner_tool="claude",
        reason="apply in progress",
        now="2026-05-03T10:00:00Z",
        ttl_seconds=60,
    )
    called = False

    def restore_files(root_path: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
        nonlocal called
        _ = root_path
        _ = checkpoint_id
        _ = relative_paths
        called = True
        return 1

    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_before",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py"],
        preview_paths=["src/app.py"],
        confirmation="APPLY ckpt_before",
        apply=True,
    )

    try:
        result = execute_recovery_apply(
            root,
            request,
            restore_files_func=restore_files,
            now="2026-05-03T10:00:10Z",
        )
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is False
    assert result.busy is True
    assert result.operation_id == active_lock.state.lock_id
    assert result.eta_seconds == 50
    assert result.would_apply is False
    assert called is False
    assert recovery_lock_path(root).exists()
    audit_payload = cast(dict[str, object], json.loads(memory_audit_path(root).read_text(encoding="utf-8")))
    assert audit_payload["event"] == "recovery_apply"
    assert audit_payload["result"] == "busy"


def test_execute_recovery_apply_aborts_when_lock_ownership_is_lost(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("broken app\n", encoding="utf-8")
    _ = (root / "src" / "settings.py").write_text("broken settings\n", encoding="utf-8")
    calls: list[tuple[str, list[str]]] = []

    def restore_files(root_path: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
        assert root_path == root
        calls.append((checkpoint_id, relative_paths))
        lock_status = read_recovery_lock(root_path)
        assert lock_status.active is True
        assert release_recovery_lock(root_path, lock_id=lock_status.state.lock_id) is True
        return len(relative_paths)

    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_before",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py", "src/settings.py"],
        preview_paths=["src/app.py", "src/settings.py"],
        confirmation="APPLY ckpt_before",
        apply=True,
    )

    try:
        result = execute_recovery_apply(root, request, restore_files_func=restore_files)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is False
    assert result.busy is False
    assert result.errors == ["recovery apply lock ownership was lost"]
    assert result.changed_files_count == 1
    assert result.changed_files == ["src/app.py"]
    assert result.would_apply is False
    assert calls == [("ckpt_before", ["src/app.py"])]
    assert not recovery_lock_path(root).exists()
    audit_line = memory_audit_path(root).read_text(encoding="utf-8").strip()
    audit_payload = cast(dict[str, object], json.loads(audit_line))
    assert audit_payload["event"] == "recovery_apply"
    assert audit_payload["result"] == "aborted"
    assert audit_payload["paths_count"] == {"drift": 0, "in_zone": 1, "total": 1}


def test_execute_recovery_apply_aborts_when_lock_ttl_expires_between_files(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("broken app\n", encoding="utf-8")
    _ = (root / "src" / "settings.py").write_text("broken settings\n", encoding="utf-8")
    calls: list[tuple[str, list[str]]] = []

    def restore_files(root_path: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
        calls.append((checkpoint_id, relative_paths))
        lock_path = recovery_lock_path(root_path)
        payload = cast(dict[str, object], json.loads(lock_path.read_text(encoding="utf-8")))
        payload["expires_at"] = "2000-01-01T00:00:00Z"
        _ = lock_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return len(relative_paths)

    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_before",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py", "src/settings.py"],
        preview_paths=["src/app.py", "src/settings.py"],
        confirmation="APPLY ckpt_before",
        apply=True,
    )

    try:
        result = execute_recovery_apply(root, request, restore_files_func=restore_files)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is False
    assert result.errors == ["recovery apply lock ownership was lost"]
    assert result.changed_files == ["src/app.py"]
    assert calls == [("ckpt_before", ["src/app.py"])]
    audit_line = memory_audit_path(root).read_text(encoding="utf-8").strip()
    audit_payload = cast(dict[str, object], json.loads(audit_line))
    assert audit_payload["result"] == "aborted"


def test_execute_recovery_apply_aborts_when_competing_owner_replaces_lock(tmp_path: Path) -> None:
    old_value = os.environ.get("VIBELIGN_RECOVERY_APPLY")
    os.environ["VIBELIGN_RECOVERY_APPLY"] = "true"
    root = tmp_path / "repo"
    _ = (root / "src").mkdir(parents=True)
    _ = (root / "src" / "app.py").write_text("broken app\n", encoding="utf-8")
    _ = (root / "src" / "settings.py").write_text("broken settings\n", encoding="utf-8")

    def restore_files(root_path: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
        _ = checkpoint_id
        _ = relative_paths
        lock_status = read_recovery_lock(root_path)
        assert release_recovery_lock(root_path, lock_id=lock_status.state.lock_id) is True
        replacement = acquire_recovery_lock(root_path, owner_tool="cursor", reason="competing apply")
        assert replacement.acquired is True
        return 1

    request = RecoveryApplyRequest(
        checkpoint_id="ckpt_before",
        sandwich_checkpoint_id="ckpt_safety",
        paths=["src/app.py", "src/settings.py"],
        preview_paths=["src/app.py", "src/settings.py"],
        confirmation="APPLY ckpt_before",
        apply=True,
    )

    try:
        result = execute_recovery_apply(root, request, restore_files_func=restore_files)
    finally:
        if old_value is None:
            _ = os.environ.pop("VIBELIGN_RECOVERY_APPLY", None)
        else:
            os.environ["VIBELIGN_RECOVERY_APPLY"] = old_value

    assert result.ok is False
    assert result.errors == ["recovery apply lock ownership was lost"]
    assert read_recovery_lock(root).active is True
