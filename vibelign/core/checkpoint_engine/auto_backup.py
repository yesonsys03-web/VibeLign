# === ANCHOR: CHECKPOINT_ENGINE_AUTO_BACKUP_START ===
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from vibelign.core.checkpoint_engine.router import create_checkpoint


AUTO_BACKUP_DB_KEY = "auto_backup_on_commit"


@dataclass(frozen=True)
class AutoBackupResult:
    status: str
    checkpoint_id: str | None = None
    warning: str | None = None


def is_auto_backup_enabled(root: Path) -> bool:
    db_path = root / ".vibelign" / "vibelign.db"
    if not db_path.exists():
        return True
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        row = conn.execute(
            "SELECT value FROM db_meta WHERE key = ?", (AUTO_BACKUP_DB_KEY,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return True
    return str(row[0]).strip() != "0"


def set_auto_backup_enabled(root: Path, enabled: bool) -> None:
    vibelign_dir = root / ".vibelign"
    vibelign_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(vibelign_dir / "vibelign.db")
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO db_meta(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (AUTO_BACKUP_DB_KEY, "1" if enabled else "0"),
        )
        conn.commit()
    finally:
        conn.close()


def create_post_commit_backup(
    root: Path, commit_sha: str, commit_message: str
) -> AutoBackupResult:
    if not is_auto_backup_enabled(root):
        return AutoBackupResult(status="disabled")
    clean_message = commit_message.strip()
    display_sha = commit_sha[:12] if commit_sha else "unknown"
    message = f"vibelign: auto backup after commit {display_sha}"
    try:
        summary = create_checkpoint(
            root,
            message,
            trigger="post_commit",
            git_commit_sha=commit_sha,
            git_commit_message=clean_message,
        )
    except RuntimeError as exc:
        return AutoBackupResult(status="warning", warning=str(exc))
    if summary is None:
        return AutoBackupResult(status="no_changes")
    return AutoBackupResult(status="created", checkpoint_id=summary.checkpoint_id)


# === ANCHOR: CHECKPOINT_ENGINE_AUTO_BACKUP_END ===
