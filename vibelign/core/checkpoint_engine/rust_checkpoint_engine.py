# === ANCHOR: CHECKPOINT_ENGINE_RUST_CHECKPOINT_ENGINE_START ===
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from vibelign.core.checkpoint_engine.contracts import CheckpointSummary, RetentionPolicy
from vibelign.core.checkpoint_engine.python_engine import PythonCheckpointEngine
from vibelign.core.checkpoint_engine.rust_engine import (
    create_checkpoint_with_rust,
    list_checkpoints_with_rust,
    prune_checkpoints_with_rust,
    restore_checkpoint_with_rust,
)
from vibelign.core.local_checkpoints import DEFAULT_RETENTION_POLICY
from vibelign.core.meta_paths import MetaPaths


_ENV_FALLBACK_MARKERS = (
    "RUST_ENGINE_UNAVAILABLE",
    "RUST_ENGINE_STARTUP_FAILED",
    "RUST_ENGINE_PROCESS_FAILED",
)


class RustCheckpointEngine:
    """Rust/SQLite checkpoint engine with visible Python fallback for environment failures."""

    def __init__(self, fallback: PythonCheckpointEngine | None = None) -> None:
        self._fallback: PythonCheckpointEngine = fallback or PythonCheckpointEngine()
        self._last_restore_error: str = ""

    def create_checkpoint(self, root: Path, message: str) -> CheckpointSummary | None:
        if _rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.create_checkpoint(root, message)
        summary, warning = create_checkpoint_with_rust(root, message)
        if summary is None:
            if warning is None:
                _record_engine_state(root, "rust", None)
                return None
            if _is_environment_fallback(warning):
                self._record_fallback(root, warning or "rust checkpoint unavailable")
                return self._fallback.create_checkpoint(root, message)
            raise RuntimeError(warning)
        pruned, prune_warning = prune_checkpoints_with_rust(
            root, DEFAULT_RETENTION_POLICY.keep_latest
        )
        if pruned is None and prune_warning and _is_environment_fallback(prune_warning):
            self._record_fallback(root, prune_warning)
        elif pruned is not None:
            summary.pruned_count = pruned["count"]
            summary.pruned_bytes = pruned["bytes"]
        _record_engine_state(root, "rust", None)
        return summary

    def list_checkpoints(self, root: Path) -> list[CheckpointSummary]:
        if _rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.list_checkpoints(root)
        checkpoints, warning = list_checkpoints_with_rust(root)
        if checkpoints is None:
            if _is_environment_fallback(warning):
                self._record_fallback(root, warning or "rust checkpoint unavailable")
                return self._fallback.list_checkpoints(root)
            raise RuntimeError(warning or "Rust checkpoint list failed.")
        _record_engine_state(root, "rust", None)
        return checkpoints

    def restore_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        self._last_restore_error = ""
        if _rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.restore_checkpoint(root, checkpoint_id)
        ok, warning = restore_checkpoint_with_rust(root, checkpoint_id)
        if ok:
            _record_engine_state(root, "rust", None)
            return True
        if _is_environment_fallback(warning):
            self._record_fallback(root, warning or "rust checkpoint unavailable")
            return self._fallback.restore_checkpoint(root, checkpoint_id)
        self._last_restore_error = warning or "Rust checkpoint restore failed."
        return False

    def has_changes_since_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return self._fallback.has_changes_since_checkpoint(root, checkpoint_id)

    def prune_checkpoints(
        self, root: Path, policy: RetentionPolicy = DEFAULT_RETENTION_POLICY
    ) -> dict[str, int]:
        if _rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.prune_checkpoints(root, policy)
        result, warning = prune_checkpoints_with_rust(root, policy.keep_latest)
        if result is None:
            if _is_environment_fallback(warning):
                self._record_fallback(root, warning or "rust checkpoint unavailable")
                return self._fallback.prune_checkpoints(root, policy)
            raise RuntimeError(warning or "Rust checkpoint prune failed.")
        _record_engine_state(root, "rust", None)
        return result

    def get_last_restore_error(self) -> str:
        return self._last_restore_error or self._fallback.get_last_restore_error()

    def friendly_time(self, created_at: str) -> str:
        parsed = _parse_rust_time(created_at)
        if parsed is None:
            return self._fallback.friendly_time(created_at)
        local_time = parsed.astimezone()
        now = datetime.now(timezone.utc).astimezone()
        delta = now - local_time
        time_str = local_time.strftime("%H:%M:%S")
        if delta.days == 0:
            return f"오늘 {time_str}"
        if delta.days == 1:
            return f"어제 {time_str}"
        if delta.days < 7:
            days = ["월", "화", "수", "목", "금", "토", "일"]
            return f"{local_time.month}월 {local_time.day}일({days[local_time.weekday()]}) {time_str}"
        return local_time.strftime("%Y-%m-%d %H:%M:%S")

    def _record_fallback(self, root: Path, reason: str) -> None:
        _record_engine_state(root, "python", reason)
        print(f"[WARN] Rust checkpoint fallback: {reason}", file=sys.stderr)


def _rust_disabled() -> bool:
    return os.environ.get("VIBELIGN_DISABLE_RUST_CHECKPOINT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _is_environment_fallback(reason: str | None) -> bool:
    if not reason:
        return False
    return any(marker in reason for marker in _ENV_FALLBACK_MARKERS)


def _record_engine_state(root: Path, engine_used: str, reason: str | None) -> None:
    state_path = MetaPaths(root).state_path
    state: dict[str, object] = {}
    try:
        if state_path.exists():
            loaded = cast(object, json.loads(state_path.read_text(encoding="utf-8")))
            if isinstance(loaded, dict):
                state = cast(dict[str, object], loaded)
    except (OSError, json.JSONDecodeError):
        state = {}
    state["engine_used"] = engine_used
    if reason:
        state["last_fallback_reason"] = reason
    elif engine_used == "rust":
        _ = state.pop("last_fallback_reason", None)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        _ = state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"[WARN] checkpoint engine state write failed: {exc}", file=sys.stderr)


def _parse_rust_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# === ANCHOR: CHECKPOINT_ENGINE_RUST_CHECKPOINT_ENGINE_END ===
