from pathlib import Path

from vibelign.core.recovery.locks import (
    acquire_recovery_lock,
    read_recovery_lock,
    recovery_lock_path,
    release_recovery_lock,
    RecoveryLockState,
)


def test_recovery_lock_path_targets_local_recovery_metadata(tmp_path: Path) -> None:
    path = recovery_lock_path(tmp_path)

    assert path == tmp_path / ".vibelign" / "recovery" / "recovery.lock.json"
    assert not path.exists()


def test_recovery_lock_state_is_metadata_only_default() -> None:
    state = RecoveryLockState()

    assert state.lock_id == ""
    assert state.created_at == ""
    assert state.owner_tool == ""
    assert state.reason == ""
    assert state.metadata_only is True


def test_acquire_recovery_lock_writes_lock_metadata(tmp_path: Path) -> None:
    result = acquire_recovery_lock(
        tmp_path,
        owner_tool="claude",
        reason="recovery apply",
        now="2026-05-03T10:00:00Z",
        ttl_seconds=60,
    )

    assert result.acquired is True
    assert result.busy is False
    assert result.state.lock_id.startswith("recovery_lock_")
    assert result.state.owner_tool == "claude"
    assert result.state.reason == "recovery apply"
    assert result.state.created_at == "2026-05-03T10:00:00Z"
    assert result.state.expires_at == "2026-05-03T10:01:00Z"
    assert result.state.metadata_only is False
    assert recovery_lock_path(tmp_path).exists()

    status = read_recovery_lock(tmp_path, now="2026-05-03T10:00:30Z")
    assert status.active is True
    assert status.expired is False
    assert status.state.lock_id == result.state.lock_id


def test_acquire_recovery_lock_returns_busy_when_active_lock_exists(tmp_path: Path) -> None:
    first = acquire_recovery_lock(
        tmp_path,
        owner_tool="claude",
        reason="first",
        now="2026-05-03T10:00:00Z",
        ttl_seconds=60,
    )

    second = acquire_recovery_lock(
        tmp_path,
        owner_tool="cursor",
        reason="second",
        now="2026-05-03T10:00:10Z",
        ttl_seconds=60,
    )

    assert second.acquired is False
    assert second.busy is True
    assert second.state.lock_id == first.state.lock_id
    assert second.operation_id == first.state.lock_id
    assert second.eta_seconds == 50


def test_expired_recovery_lock_can_be_replaced_and_release_requires_matching_id(tmp_path: Path) -> None:
    first = acquire_recovery_lock(
        tmp_path,
        owner_tool="claude",
        reason="first",
        now="2026-05-03T10:00:00Z",
        ttl_seconds=60,
    )

    expired = read_recovery_lock(tmp_path, now="2026-05-03T10:02:00Z")
    assert expired.active is False
    assert expired.expired is True

    second = acquire_recovery_lock(
        tmp_path,
        owner_tool="cursor",
        reason="second",
        now="2026-05-03T10:02:00Z",
        ttl_seconds=60,
    )
    assert second.acquired is True
    assert second.state.lock_id != first.state.lock_id

    assert release_recovery_lock(tmp_path, lock_id=first.state.lock_id) is False
    assert recovery_lock_path(tmp_path).exists()
    assert release_recovery_lock(tmp_path, lock_id=second.state.lock_id) is True
    assert not recovery_lock_path(tmp_path).exists()
