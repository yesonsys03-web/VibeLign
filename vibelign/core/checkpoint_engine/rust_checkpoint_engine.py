# === ANCHOR: CHECKPOINT_ENGINE_RUST_CHECKPOINT_ENGINE_START ===
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from vibelign.core.checkpoint_engine.contracts import CheckpointSummary, RetentionPolicy
from vibelign.core.checkpoint_engine.fallback_policy import (
    is_environment_fallback,
    is_protocol_compatibility_fallback,
    record_engine_state,
    rust_disabled,
    rust_required,
)
from vibelign.core.checkpoint_engine.python_engine import PythonCheckpointEngine
from vibelign.core.checkpoint_engine.rust_engine import (
    apply_retention_with_rust,
    backup_graph_summary_with_rust,
    create_checkpoint_with_rust,
    diff_checkpoints_with_rust,
    inspect_backup_db_with_rust,
    list_checkpoints_with_rust,
    maintain_backup_db_with_rust,
    preview_restore_with_rust,
    prune_checkpoints_with_rust,
    restore_checkpoint_with_rust,
    restore_files_with_rust,
    restore_suggestions_with_rust,
)
from vibelign.core.local_checkpoints import DEFAULT_RETENTION_POLICY
class RustCheckpointEngine:
    """Rust/SQLite checkpoint engine with visible Python fallback for environment failures."""

    def __init__(self, fallback: PythonCheckpointEngine | None = None) -> None:
        self._fallback: PythonCheckpointEngine = fallback or PythonCheckpointEngine()
        self._last_restore_error: str = ""

    def create_checkpoint(
        self,
        root: Path,
        message: str,
        *,
        trigger: str | None = None,
        git_commit_sha: str | None = None,
        git_commit_message: str | None = None,
    ) -> CheckpointSummary | None:
        if rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.create_checkpoint(
                root,
                message,
                trigger=trigger,
                git_commit_sha=git_commit_sha,
                git_commit_message=git_commit_message,
            )
        summary, warning = create_checkpoint_with_rust(
            root,
            message,
            trigger=trigger,
            git_commit_sha=git_commit_sha,
            git_commit_message=git_commit_message,
        )
        if summary is None:
            if warning is None:
                record_engine_state(root, "rust", None)
                return None
            if is_environment_fallback(warning):
                if rust_required():
                    raise RuntimeError(warning)
                self._record_fallback(root, warning or "rust checkpoint unavailable")
                return self._fallback.create_checkpoint(
                    root,
                    message,
                    trigger=trigger,
                    git_commit_sha=git_commit_sha,
                    git_commit_message=git_commit_message,
                )
            raise RuntimeError(warning)
        pruned, prune_warning = prune_checkpoints_with_rust(
            root, DEFAULT_RETENTION_POLICY.keep_latest
        )
        if pruned is None and prune_warning and is_environment_fallback(prune_warning):
            self._record_fallback(root, prune_warning)
        elif pruned is not None:
            summary.pruned_count = pruned["count"]
            summary.pruned_bytes = pruned["bytes"]
        record_engine_state(root, "rust", None)
        return summary

    def list_checkpoints(self, root: Path) -> list[CheckpointSummary]:
        if rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.list_checkpoints(root)
        checkpoints, warning = list_checkpoints_with_rust(root)
        if checkpoints is None:
            if is_environment_fallback(warning):
                if rust_required():
                    raise RuntimeError(warning or "rust checkpoint unavailable")
                self._record_fallback(root, warning or "rust checkpoint unavailable")
                return self._fallback.list_checkpoints(root)
            raise RuntimeError(warning or "Rust checkpoint list failed.")
        fallback_checkpoints = self._fallback.list_checkpoints(root)
        if fallback_checkpoints:
            existing_ids = {checkpoint.checkpoint_id for checkpoint in checkpoints}
            legacy_only = [
                checkpoint
                for checkpoint in fallback_checkpoints
                if checkpoint.checkpoint_id not in existing_ids
            ]
            if legacy_only:
                record_engine_state(root, "python", "legacy Python checkpoints visible")
                return [*checkpoints, *legacy_only]
        record_engine_state(root, "rust", None)
        return checkpoints

    def restore_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        self._last_restore_error = ""
        if rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.restore_checkpoint(root, checkpoint_id)
        ok, warning = restore_checkpoint_with_rust(root, checkpoint_id)
        if ok:
            record_engine_state(root, "rust", None)
            return True
        if is_environment_fallback(warning):
            if rust_required():
                self._last_restore_error = warning or "rust checkpoint unavailable"
                return False
            self._record_fallback(root, warning or "rust checkpoint unavailable")
            return self._fallback.restore_checkpoint(root, checkpoint_id)
        if any(
            checkpoint.checkpoint_id == checkpoint_id
            for checkpoint in self._fallback.list_checkpoints(root)
        ):
            self._record_fallback(
                root,
                f"legacy Python checkpoint restore fallback: {warning or 'rust checkpoint restore failed'}",
            )
            return self._fallback.restore_checkpoint(root, checkpoint_id)
        self._last_restore_error = warning or "Rust checkpoint restore failed."
        return False

    def diff_checkpoints(
        self, root: Path, from_checkpoint_id: str, to_checkpoint_id: str
    ) -> dict[str, object]:
        result, warning = diff_checkpoints_with_rust(root, from_checkpoint_id, to_checkpoint_id)
        if result is None:
            raise RuntimeError(warning or "Rust checkpoint diff failed.")
        record_engine_state(root, "rust", None)
        return result

    def preview_restore(
        self, root: Path, checkpoint_id: str, relative_paths: list[str] | None = None
    ) -> dict[str, object]:
        result, warning = preview_restore_with_rust(root, checkpoint_id, relative_paths)
        if result is None:
            raise RuntimeError(warning or "Rust checkpoint preview failed.")
        record_engine_state(root, "rust", None)
        return result

    def restore_files(self, root: Path, checkpoint_id: str, relative_paths: list[str]) -> int:
        count, warning = restore_files_with_rust(root, checkpoint_id, relative_paths)
        if count is None:
            raise RuntimeError(warning or "Rust selected restore failed.")
        record_engine_state(root, "rust", None)
        return count

    def restore_suggestions(
        self, root: Path, checkpoint_id: str, cap: int = 5
    ) -> dict[str, object]:
        result, warning = restore_suggestions_with_rust(root, checkpoint_id, cap)
        if result is None:
            raise RuntimeError(warning or "Rust checkpoint suggestions failed.")
        record_engine_state(root, "rust", None)
        return result

    def has_changes_since_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return self._fallback.has_changes_since_checkpoint(root, checkpoint_id)

    def prune_checkpoints(
        self, root: Path, policy: RetentionPolicy = DEFAULT_RETENTION_POLICY
    ) -> dict[str, int]:
        if rust_disabled():
            self._record_fallback(root, "rust checkpoint disabled by environment")
            return self._fallback.prune_checkpoints(root, policy)
        result, warning = prune_checkpoints_with_rust(root, policy.keep_latest)
        if result is None:
            if is_environment_fallback(warning):
                if rust_required():
                    raise RuntimeError(warning or "rust checkpoint unavailable")
                self._record_fallback(root, warning or "rust checkpoint unavailable")
                return self._fallback.prune_checkpoints(root, policy)
            raise RuntimeError(warning or "Rust checkpoint prune failed.")
        record_engine_state(root, "rust", None)
        return result

    def apply_retention(self, root: Path) -> dict[str, object]:
        result, warning = apply_retention_with_rust(root)
        if result is None:
            if is_environment_fallback(warning):
                if rust_required():
                    raise RuntimeError(warning or "rust checkpoint unavailable")
                self._record_fallback(root, warning or "rust checkpoint unavailable")
                pruned = self._fallback.prune_checkpoints(
                    root, DEFAULT_RETENTION_POLICY
                )
                return {"count": pruned["count"], "bytes": pruned["bytes"]}
            raise RuntimeError(warning or "Rust retention cleanup failed.")
        record_engine_state(root, "rust", None)
        return result

    def inspect_backup_db(self, root: Path) -> dict[str, object]:
        result, warning = inspect_backup_db_with_rust(root)
        if result is None:
            if is_environment_fallback(warning) or is_protocol_compatibility_fallback(warning):
                self._record_fallback(root, warning or "rust backup DB viewer unavailable")
                return self._fallback.inspect_backup_db(root)
            raise RuntimeError(warning or "Rust backup DB viewer inspect failed.")
        record_engine_state(root, "rust", None)
        return result

    def maintain_backup_db(self, root: Path, *, apply: bool = False) -> dict[str, object]:
        result, warning = maintain_backup_db_with_rust(root, apply=apply)
        if result is None:
            raise RuntimeError(warning or "Rust backup DB maintenance failed.")
        record_engine_state(root, "rust", None)
        return result

    def backup_graph_summary(self, root: Path) -> dict[str, object]:
        result, warning = backup_graph_summary_with_rust(root)
        if result is None:
            if is_environment_fallback(warning) or is_protocol_compatibility_fallback(warning):
                self._record_fallback(root, warning or "rust backup graph summary unavailable")
                return self._fallback.backup_graph_summary(root)
            raise RuntimeError(warning or "Rust backup graph summary failed.")
        record_engine_state(root, "rust", None)
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
        record_engine_state(root, "python", reason)
        print(f"[WARN] Rust checkpoint fallback: {reason}", file=sys.stderr)
def _parse_rust_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# === ANCHOR: CHECKPOINT_ENGINE_RUST_CHECKPOINT_ENGINE_END ===
