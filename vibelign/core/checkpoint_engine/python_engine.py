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

    def inspect_backup_db(self, root: Path) -> dict[str, object]:
        db_path = root / ".vibelign" / "vibelign.db"
        object_store_path = root / ".vibelign" / "rust_objects" / "blake3"
        warnings: list[str] = []
        db_file = _backup_db_file_stats(db_path)
        if not db_path.exists():
            warnings.append("Rust backup DB가 아직 없어요. 백업을 먼저 만들어 주세요.")
            return _empty_backup_db_report(db_path, object_store_path, db_file, warnings)
        if db_path.is_symlink():
            raise RuntimeError("Backup DB Viewer refuses to follow symlinks")
        try:
            conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Backup DB Viewer read failed: {exc}") from exc
        try:
            try:
                conn.execute("PRAGMA query_only = true")
            except sqlite3.Error as exc:
                warnings.append(
                    f"query_only pragma를 적용하지 못했지만 read-only connection으로 계속 표시합니다: {exc}"
                )
            tables = _sqlite_tables(conn)
            columns = {table: _sqlite_columns(conn, table) for table in tables}
            schema_version = _read_db_meta(conn, tables, "schema_version")
            _add_backup_db_size_warnings(db_file["total_bytes"], warnings)
            if "checkpoints" not in tables:
                warnings.append("checkpoints table이 없어 백업 row 요약을 0으로 표시합니다.")
            if "cas_objects" not in tables:
                warnings.append("cas_objects table이 없어 object store 요약을 0으로 표시합니다.")
            if "retention_policy" not in tables:
                warnings.append("retention_policy table이 없어 정리 정책을 표시하지 않습니다.")
            return {
                "result": "backup_db_viewer_inspect",
                "db_exists": True,
                "db_path": str(db_path),
                "db_file": db_file,
                "schema_version": schema_version,
                "checkpoint_count": _sqlite_count(conn, tables, "checkpoints"),
                "rust_v2_count": _sqlite_where_count(
                    conn,
                    tables,
                    columns,
                    "checkpoints",
                    "engine_version",
                    "engine_version = 'rust-v2'",
                ),
                "legacy_count": _sqlite_legacy_count(conn, tables, columns),
                "cas_object_count": _sqlite_count(conn, tables, "cas_objects"),
                "cas_ref_count": _sqlite_sum(conn, tables, columns, "cas_objects", "ref_count"),
                "total_original_size_bytes": _sqlite_sum(
                    conn, tables, columns, "checkpoints", "original_size_bytes"
                ),
                "total_stored_size_bytes": _sqlite_sum(
                    conn, tables, columns, "checkpoints", "stored_size_bytes"
                ),
                "auto_backup_on_commit": _read_db_meta(conn, tables, "auto_backup_on_commit")
                in {"1", "true", "TRUE", "yes", "YES"},
                "retention_policy": _load_backup_retention_policy(conn, tables, columns, warnings),
                "object_store": _load_backup_object_store(conn, tables, columns, object_store_path),
                "checkpoints": _load_backup_checkpoint_rows(conn, tables, columns, warnings),
                "warnings": warnings,
            }
        finally:
            conn.close()

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


def _backup_db_file_stats(db_path: Path) -> dict[str, int]:
    database_bytes = _file_size(db_path)
    wal_bytes = _file_size(db_path.with_name("vibelign.db-wal"))
    shm_bytes = _file_size(db_path.with_name("vibelign.db-shm"))
    return {
        "database_bytes": database_bytes,
        "wal_bytes": wal_bytes,
        "shm_bytes": shm_bytes,
        "total_bytes": database_bytes + wal_bytes + shm_bytes,
    }


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _empty_backup_db_report(
    db_path: Path,
    object_store_path: Path,
    db_file: dict[str, int],
    warnings: list[str],
) -> dict[str, object]:
    return {
        "result": "backup_db_viewer_inspect",
        "db_exists": False,
        "db_path": str(db_path),
        "db_file": db_file,
        "schema_version": None,
        "checkpoint_count": 0,
        "rust_v2_count": 0,
        "legacy_count": 0,
        "cas_object_count": 0,
        "cas_ref_count": 0,
        "total_original_size_bytes": 0,
        "total_stored_size_bytes": 0,
        "auto_backup_on_commit": False,
        "retention_policy": None,
        "object_store": {
            "exists": object_store_path.exists(),
            "path": str(object_store_path),
            "compression_summary": [],
            "stored_size_bytes": 0,
            "original_size_bytes": 0,
        },
        "checkpoints": [],
        "warnings": warnings,
    }


def _sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _read_db_meta(conn: sqlite3.Connection, tables: set[str], key: str) -> str | None:
    if "db_meta" not in tables:
        return None
    row = conn.execute("SELECT value FROM db_meta WHERE key = ?", (key,)).fetchone()
    return str(row[0]) if row is not None and row[0] is not None else None


def _add_backup_db_size_warnings(total_bytes: int, warnings: list[str]) -> None:
    if total_bytes >= 256 * 1024 * 1024:
        warnings.append("백업 관리 DB 파일이 256MB를 넘었어요. 백업 정리 뒤 DB 압축/정리 정책이 필요합니다.")
    elif total_bytes >= 64 * 1024 * 1024:
        warnings.append("백업 관리 DB 파일이 64MB를 넘었어요. 계속 커지면 DB 압축/정리 정책을 검토하세요.")


def _sqlite_count(conn: sqlite3.Connection, tables: set[str], table: str) -> int:
    if table not in tables:
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] or 0)


def _sqlite_where_count(
    conn: sqlite3.Connection,
    tables: set[str],
    columns: dict[str, set[str]],
    table: str,
    required_column: str,
    predicate: str,
) -> int:
    if table not in tables or required_column not in columns.get(table, set()):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {predicate}").fetchone()[0] or 0)


def _sqlite_legacy_count(
    conn: sqlite3.Connection, tables: set[str], columns: dict[str, set[str]]
) -> int:
    if "checkpoints" not in tables:
        return 0
    if "engine_version" not in columns.get("checkpoints", set()):
        return _sqlite_count(conn, tables, "checkpoints")
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE engine_version IS NULL OR engine_version != 'rust-v2'"
        ).fetchone()[0]
        or 0
    )


def _sqlite_sum(
    conn: sqlite3.Connection,
    tables: set[str],
    columns: dict[str, set[str]],
    table: str,
    column: str,
) -> int:
    if table not in tables or column not in columns.get(table, set()):
        return 0
    return int(conn.execute(f"SELECT COALESCE(SUM({column}), 0) FROM {table}").fetchone()[0] or 0)


def _load_backup_retention_policy(
    conn: sqlite3.Connection,
    tables: set[str],
    columns: dict[str, set[str]],
    warnings: list[str],
) -> dict[str, int] | None:
    required = {
        "keep_latest",
        "keep_daily_days",
        "keep_weekly_weeks",
        "max_total_size_bytes",
        "max_age_days",
        "min_keep",
    }
    if "retention_policy" not in tables:
        return None
    if not required.issubset(columns.get("retention_policy", set())):
        warnings.append("retention_policy schema가 오래되어 정리 정책을 표시하지 않습니다.")
        return None
    row = conn.execute(
        "SELECT keep_latest, keep_daily_days, keep_weekly_weeks, max_total_size_bytes, max_age_days, min_keep "
        "FROM retention_policy WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    return {
        "keep_latest": int(row[0] or 0),
        "keep_daily_days": int(row[1] or 0),
        "keep_weekly_weeks": int(row[2] or 0),
        "max_total_size_bytes": int(row[3] or 0),
        "max_age_days": int(row[4] or 0),
        "min_keep": int(row[5] or 0),
    }


def _load_backup_object_store(
    conn: sqlite3.Connection,
    tables: set[str],
    columns: dict[str, set[str]],
    object_store_path: Path,
) -> dict[str, object]:
    compression_summary: list[dict[str, object]] = []
    if "cas_objects" in tables:
        if "compression" in columns.get("cas_objects", set()):
            compression_summary = [
                {"compression": str(row[0] or "unknown"), "object_count": int(row[1] or 0)}
                for row in conn.execute(
                    "SELECT compression, COUNT(*) FROM cas_objects GROUP BY compression ORDER BY compression ASC"
                )
            ]
        else:
            count = _sqlite_count(conn, tables, "cas_objects")
            if count:
                compression_summary = [{"compression": "unknown", "object_count": count}]
    return {
        "exists": object_store_path.exists(),
        "path": str(object_store_path),
        "compression_summary": compression_summary,
        "stored_size_bytes": _sqlite_sum(conn, tables, columns, "cas_objects", "stored_size"),
        "original_size_bytes": _sqlite_sum(conn, tables, columns, "cas_objects", "size"),
    }


def _load_backup_checkpoint_rows(
    conn: sqlite3.Connection,
    tables: set[str],
    columns: dict[str, set[str]],
    warnings: list[str],
) -> list[dict[str, object]]:
    checkpoint_columns = columns.get("checkpoints", set())
    required = {"checkpoint_id", "created_at", "message", "pinned", "total_size_bytes", "file_count"}
    if "checkpoints" not in tables:
        return []
    if not required.issubset(checkpoint_columns):
        warnings.append("checkpoints schema가 오래되어 백업 row를 표시하지 않습니다.")
        return []
    select = (
        "SELECT checkpoint_id, created_at, message, pinned, total_size_bytes, file_count, "
        f"{_optional_column(checkpoint_columns, 'engine_version', 'NULL')}, "
        f"{_optional_column(checkpoint_columns, 'parent_checkpoint_id', 'NULL')}, "
        f"{_optional_column(checkpoint_columns, 'original_size_bytes', '0')}, "
        f"{_optional_column(checkpoint_columns, 'stored_size_bytes', '0')}, "
        f"{_optional_column(checkpoint_columns, 'reused_file_count', '0')}, "
        f"{_optional_column(checkpoint_columns, 'changed_file_count', '0')}, "
        f"{_optional_column(checkpoint_columns, 'trigger', 'NULL')}, "
        f"{_optional_column(checkpoint_columns, 'git_commit_sha', 'NULL')}, "
        f"{_optional_column(checkpoint_columns, 'git_commit_message', 'NULL')} "
        "FROM checkpoints ORDER BY created_at DESC, checkpoint_id DESC"
    )
    rows: list[dict[str, object]] = []
    for row in conn.execute(select):
        message = str(row[2] or "")
        trigger = str(row[12]) if row[12] is not None else None
        git_commit_message = str(row[14]) if row[14] is not None else None
        engine_version = str(row[6]) if row[6] is not None else None
        rows.append(
            {
                "checkpoint_id": str(row[0] or ""),
                "display_name": _backup_display_name(message, trigger, git_commit_message),
                "created_at": str(row[1] or ""),
                "pinned": int(row[3] or 0) != 0,
                "trigger": trigger,
                "trigger_label": _backup_trigger_label(trigger),
                "git_commit_sha": str(row[13]) if row[13] is not None else None,
                "git_commit_message": git_commit_message,
                "file_count": int(row[5] or 0),
                "total_size_bytes": int(row[4] or 0),
                "original_size_bytes": int(row[8] or 0),
                "stored_size_bytes": int(row[9] or 0),
                "reused_file_count": int(row[10] or 0),
                "changed_file_count": int(row[11] or 0),
                "engine_version": engine_version,
                "parent_checkpoint_id": str(row[7]) if row[7] is not None else None,
                "internal_badges": _backup_badges(engine_version, trigger),
            }
        )
    return rows


def _optional_column(columns: set[str], column: str, fallback: str) -> str:
    return column if column in columns else f"{fallback} AS {column}"


def _backup_trigger_label(trigger: str | None) -> str:
    if trigger == "post_commit":
        return "코드 저장 뒤 자동 보관"
    if trigger == "safe_restore":
        return "복원 보호용 내부 저장본"
    if trigger is None or trigger == "manual":
        return "수동 백업"
    return "기타"


def _backup_display_name(
    message: str, trigger: str | None, git_commit_message: str | None
) -> str:
    cleaned = _clean_backup_message(git_commit_message or message)
    if trigger == "post_commit":
        return "코드 저장 뒤 자동 보관" if not cleaned else f"코드 저장 뒤 자동 보관 - {cleaned}"
    if trigger == "safe_restore":
        return "복원 보호용 내부 저장본" if not cleaned else f"복원 보호용 내부 저장본 - {cleaned}"
    return cleaned or "메모 없는 저장본"


def _clean_backup_message(value: str) -> str:
    text = value.strip()
    lower = text.lower()
    if lower.startswith("vibelign: checkpoint"):
        text = text[len("vibelign: checkpoint") :].strip()
    return text.removeprefix("-").strip()


def _backup_badges(engine_version: str | None, trigger: str | None) -> list[str]:
    badges: list[str] = []
    if engine_version == "rust-v2":
        badges.append("Rust v2")
    elif engine_version:
        badges.append(engine_version)
    else:
        badges.append("Legacy")
    if trigger == "post_commit":
        badges.append("Auto")
    if trigger == "safe_restore":
        badges.append("Internal")
    return badges


# === ANCHOR: CHECKPOINT_ENGINE_PYTHON_ENGINE_END ===
