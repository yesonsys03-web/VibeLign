# === ANCHOR: RECOVERY_LOCKS_START ===
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4


@dataclass(frozen=True)
class RecoveryLockState:
    lock_id: str = ""
    created_at: str = ""
    expires_at: str = ""
    owner_tool: str = ""
    reason: str = ""
    metadata_only: bool = True


@dataclass(frozen=True)
class RecoveryLockStatus:
    state: RecoveryLockState
    active: bool
    expired: bool
    eta_seconds: int | None = None


@dataclass(frozen=True)
class RecoveryLockAcquireResult:
    state: RecoveryLockState
    acquired: bool
    busy: bool
    operation_id: str = ""
    eta_seconds: int | None = None


def recovery_lock_path(root: Path) -> Path:
    return root / ".vibelign" / "recovery" / "recovery.lock.json"


def acquire_recovery_lock(
    root: Path,
    *,
    owner_tool: str,
    reason: str,
    now: str | None = None,
    ttl_seconds: int = 60,
) -> RecoveryLockAcquireResult:
    current = read_recovery_lock(root, now=now)
    if current.active:
        return RecoveryLockAcquireResult(
            state=current.state,
            acquired=False,
            busy=True,
            operation_id=current.state.lock_id,
            eta_seconds=current.eta_seconds,
        )

    created_at = _normalize_timestamp(now)
    expires_at = _format_timestamp(_parse_timestamp(created_at) + timedelta(seconds=ttl_seconds))
    state = RecoveryLockState(
        lock_id=f"recovery_lock_{uuid4().hex}",
        created_at=created_at,
        expires_at=expires_at,
        owner_tool=owner_tool.strip(),
        reason=reason.strip(),
        metadata_only=False,
    )
    path = recovery_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(_state_to_dict(state), ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return RecoveryLockAcquireResult(state=state, acquired=True, busy=False, operation_id=state.lock_id, eta_seconds=ttl_seconds)


def read_recovery_lock(root: Path, *, now: str | None = None) -> RecoveryLockStatus:
    path = recovery_lock_path(root)
    if not path.exists():
        return RecoveryLockStatus(state=RecoveryLockState(), active=False, expired=False)
    state = _state_from_dict(cast("object", json.loads(path.read_text(encoding="utf-8"))))
    if not state.expires_at:
        return RecoveryLockStatus(state=state, active=True, expired=False)
    remaining = int((_parse_timestamp(state.expires_at) - _parse_timestamp(_normalize_timestamp(now))).total_seconds())
    if remaining <= 0:
        return RecoveryLockStatus(state=state, active=False, expired=True, eta_seconds=0)
    return RecoveryLockStatus(state=state, active=True, expired=False, eta_seconds=remaining)


def release_recovery_lock(root: Path, *, lock_id: str) -> bool:
    path = recovery_lock_path(root)
    if not path.exists():
        return False
    state = _state_from_dict(cast("object", json.loads(path.read_text(encoding="utf-8"))))
    if state.lock_id != lock_id:
        return False
    path.unlink()
    return True


def _state_to_dict(state: RecoveryLockState) -> dict[str, object]:
    return {
        "lock_id": state.lock_id,
        "created_at": state.created_at,
        "expires_at": state.expires_at,
        "owner_tool": state.owner_tool,
        "reason": state.reason,
        "metadata_only": state.metadata_only,
    }


def _state_from_dict(data: object) -> RecoveryLockState:
    if not isinstance(data, dict):
        return RecoveryLockState()
    values = cast("dict[object, object]", data)
    return RecoveryLockState(
        lock_id=str(values.get("lock_id", "")),
        created_at=str(values.get("created_at", "")),
        expires_at=str(values.get("expires_at", "")),
        owner_tool=str(values.get("owner_tool", "")),
        reason=str(values.get("reason", "")),
        metadata_only=bool(values.get("metadata_only", False)),
    )


def _normalize_timestamp(value: str | None) -> str:
    if value is not None:
        return _format_timestamp(_parse_timestamp(value))
    return _format_timestamp(datetime.now(UTC))


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
# === ANCHOR: RECOVERY_LOCKS_END ===
