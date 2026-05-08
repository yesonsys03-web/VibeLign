# === ANCHOR: CHECKPOINT_ENGINE_PYTHON_ENGINE_START ===
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, TypedDict

from vibelign.core import local_checkpoints
from vibelign.core.checkpoint_engine.contracts import CheckpointSummary, RetentionPolicy


class _GraphNode(TypedDict):
    id: str
    name: str
    path: str
    size_bytes: int
    children: list["_GraphNode"]


class _GraphNodeBuilder:
    def __init__(self, name: str, path: str) -> None:
        self.name = name
        self.path = path
        self.size_bytes = 0
        self.children: DefaultDict[str, _GraphNodeBuilder] = defaultdict(
            lambda: _GraphNodeBuilder("", "")
        )

    def child(self, name: str, path: str) -> "_GraphNodeBuilder":
        child = self.children[name]
        if not child.name:
            child.name = name
            child.path = path
        return child

    def to_dict(self) -> _GraphNode:
        children = sorted(
            (child.to_dict() for child in self.children.values()),
            key=lambda item: (-item["size_bytes"], item["name"]),
        )
        return {
            "id": self.path or "root",
            "name": self.name or "백업",
            "path": self.path,
            "size_bytes": self.size_bytes,
            "children": children,
        }


class PythonCheckpointEngine:
    """Adapter for the current Python checkpoint implementation."""

    def create_checkpoint(
        self,
        root: Path,
        message: str,
        *,
        trigger: str | None = None,
        git_commit_sha: str | None = None,
        git_commit_message: str | None = None,
    ) -> CheckpointSummary | None:
        return local_checkpoints.create_checkpoint(
            root,
            message,
            trigger=trigger,
            git_commit_sha=git_commit_sha,
            git_commit_message=git_commit_message,
        )

    def list_checkpoints(self, root: Path) -> list[CheckpointSummary]:
        return local_checkpoints.list_checkpoints(root)

    def restore_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return local_checkpoints.restore_checkpoint(root, checkpoint_id)

    def diff_checkpoints(
        self, _root: Path, _from_checkpoint_id: str, _to_checkpoint_id: str
    ) -> dict[str, object]:
        raise RuntimeError("checkpoint diff is not available")

    def preview_restore(
        self, _root: Path, _checkpoint_id: str, _relative_paths: list[str] | None = None
    ) -> dict[str, object]:
        raise RuntimeError("checkpoint preview is not available")

    def restore_files(
        self, _root: Path, _checkpoint_id: str, _relative_paths: list[str]
    ) -> int:
        raise RuntimeError("selected checkpoint restore is not available")

    def restore_suggestions(
        self, _root: Path, _checkpoint_id: str, _cap: int = 5
    ) -> dict[str, object]:
        raise RuntimeError("checkpoint restore suggestions are not available")

    def has_changes_since_checkpoint(self, root: Path, checkpoint_id: str) -> bool:
        return local_checkpoints.has_changes_since_checkpoint(root, checkpoint_id)

    def prune_checkpoints(
        self, root: Path, policy: RetentionPolicy = local_checkpoints.DEFAULT_RETENTION_POLICY
    ) -> dict[str, int]:
        return local_checkpoints.prune_checkpoints(root, policy)

    def apply_retention(self, root: Path) -> dict[str, object]:
        pruned = local_checkpoints.prune_checkpoints(
            root, local_checkpoints.DEFAULT_RETENTION_POLICY
        )
        return {"count": pruned["count"], "bytes": pruned["bytes"]}

    def inspect_backup_db(self, _root: Path) -> dict[str, object]:
        raise RuntimeError("Backup DB Viewer requires the Rust checkpoint engine")

    def maintain_backup_db(self, _root: Path, *, apply: bool = False) -> dict[str, object]:
        _ = apply
        raise RuntimeError("Backup DB maintenance requires the Rust checkpoint engine")

    def backup_graph_summary(self, root: Path) -> dict[str, object]:
        db_path = root / ".vibelign" / "vibelign.db"
        warnings: list[str] = []
        graph_root = _GraphNodeBuilder("백업", "")
        if not db_path.exists():
            warnings.append("Rust backup DB가 아직 없어요. 백업을 먼저 만들어 주세요.")
            return {
                "result": "backup_graph_summary",
                "db_exists": False,
                "file_row_count": 0,
                "root": graph_root.to_dict(),
                "warnings": warnings,
            }
        if db_path.is_symlink():
            raise RuntimeError("Backup graph summary refuses to follow symlinks")
        try:
            conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Backup graph summary read failed: {exc}") from exc
        try:
            try:
                conn.execute("PRAGMA query_only = true")
            except sqlite3.Error as exc:
                warnings.append(
                    f"query_only pragma를 적용하지 못했지만 read-only connection으로 계속 표시합니다: {exc}"
                )
            table_row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='checkpoint_files'"
            ).fetchone()
            if table_row is None:
                warnings.append("checkpoint_files table이 없어 백업 범위 그래프를 표시하지 않습니다.")
                return {
                    "result": "backup_graph_summary",
                    "db_exists": True,
                    "file_row_count": 0,
                    "root": graph_root.to_dict(),
                    "warnings": warnings,
                }
            row_count = 0
            for raw_path, size in conn.execute(
                "SELECT relative_path, size FROM checkpoint_files WHERE size > 0 ORDER BY relative_path ASC"
            ):
                if not isinstance(raw_path, str):
                    continue
                normalized = _normalize_graph_path(raw_path)
                size_bytes = int(size or 0)
                if not normalized or size_bytes <= 0:
                    continue
                row_count += 1
                graph_root.size_bytes += size_bytes
                current = graph_root
                parts: list[str] = []
                for part in normalized.split("/"):
                    parts.append(part)
                    current = current.child(part, "/".join(parts))
                    current.size_bytes += size_bytes
        finally:
            conn.close()
        return {
            "result": "backup_graph_summary",
            "db_exists": True,
            "file_row_count": row_count,
            "root": graph_root.to_dict(),
            "warnings": warnings,
        }

    def get_last_restore_error(self) -> str:
        return local_checkpoints.get_last_restore_error()

    def friendly_time(self, created_at: str) -> str:
        return local_checkpoints.friendly_time(created_at)


def _normalize_graph_path(path: str) -> str:
    return "/".join(
        part for part in path.replace("\\", "/").split("/") if part and part not in {".", ".."}
    )


# === ANCHOR: CHECKPOINT_ENGINE_PYTHON_ENGINE_END ===
