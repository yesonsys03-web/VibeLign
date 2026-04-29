# === ANCHOR: TRANSFER_GIT_CONTEXT_START ===
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.structure_policy import (
    HANDOFF_SKIP_EXTENSIONS,
    HANDOFF_SKIP_PREFIXES,
    TRANSFER_TREE_IGNORED_DIRS,
    WINDOWS_SUBPROCESS_FLAGS,
)
from vibelign.core.work_memory import load_work_memory
from vibelign.core.work_memory import WorkMemoryState

_SKIP_DIRS_LOWER = {item.lower() for item in TRANSFER_TREE_IGNORED_DIRS}
_SKIP_EXTS = set(HANDOFF_SKIP_EXTENSIONS)
_HANDOFF_SKIP_DIR_SUFFIXES = (".egg-info",)


class DetailedCommit(TypedDict):
    hash: str
    message: str
    files: str


class WorkingTreeSummary(TypedDict):
    count: int
    files: list[str]
    details: list[str]
    summary: str | None


def should_include_handoff_path(path: str) -> bool:
    normalized_path = path.replace("\\", "/").strip()
    if not normalized_path or any(
        normalized_path == prefix or normalized_path.startswith(f"{prefix}/")
        for prefix in HANDOFF_SKIP_PREFIXES
    ):
        return False
    if normalized_path.endswith((".pyc", ".pyo")):
        return False
    for part in normalized_path.split("/"):
        normalized_part = part.lower()
        if normalized_part in _SKIP_DIRS_LOWER:
            return False
        if any(normalized_part.endswith(suffix) for suffix in _HANDOFF_SKIP_DIR_SUFFIXES):
            return False
    return True


def get_changed_files(root: Path) -> list[str]:
    """Return git working-tree paths that are safe to include in handoff."""
    return get_working_tree_summary(root, max_items=10)["files"]


def get_working_tree_summary(root: Path, max_items: int = 20) -> WorkingTreeSummary:
    """Return one git-status-backed source of truth for handoff dirty state."""
    files: list[str] = []
    details: list[str] = []
    stats = _working_tree_numstat(root)
    try:
        status_result = subprocess.run(
            ["git", "-c", "core.quotePath=false", "status", "--porcelain", "-uall"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
    except Exception:
        return {"count": 0, "files": [], "details": [], "summary": None}

    for line in status_result.stdout.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        raw_path = line[3:].strip()
        path = raw_path.split(" -> ")[-1]
        if not should_include_handoff_path(path) or path in files:
            continue
        files.append(path)
        detail = f"{path} — {_status_label(code)}"
        stat = stats.get(path) or stats.get(raw_path)
        if stat:
            detail += f" ({stat})"
        details.append(detail)

    count = len(files)
    return {
        "count": count,
        "files": files[:max_items],
        "details": details[:max_items],
        "summary": f"커밋되지 않은 변경 {count}개 파일" if count else None,
    }


def get_working_tree_change_details(root: Path) -> list[str]:
    """Return concise git working-tree details for handoff continuation."""
    return get_working_tree_summary(root)["details"]


def get_recent_commits(root: Path, n: int = 5) -> list[str]:
    """Return recent user commit messages, excluding VibeLign auto commits."""
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={n * 2}", "--pretty=format:%s", "--no-merges"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        messages = [item.strip() for item in result.stdout.splitlines() if item.strip()]
        return [message for message in messages if not message.startswith("vibelign:")][:n]
    except Exception:
        return []


def get_detailed_commits(root: Path, n: int = 10) -> list[DetailedCommit]:
    """Return recent commit hashes, messages, and changed files for handoff context."""
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.quotePath=false",
                "log",
                f"--max-count={n * 2}",
                "--pretty=format:%h\t%s",
                "--no-merges",
                "--name-only",
            ],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=10,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        commits: list[DetailedCommit] = []
        current: DetailedCommit | None = None
        for line in result.stdout.splitlines():
            if "\t" in line:
                if current and not current["message"].startswith("vibelign:"):
                    commits.append(current)
                commit_hash, message = line.split("\t", 1)
                current = {"hash": commit_hash, "message": message, "files": ""}
            elif line.strip() and current is not None:
                fname = line.strip()
                if should_include_handoff_path(fname):
                    if current["files"]:
                        current["files"] += ", "
                    current["files"] += fname
        if current and not current["message"].startswith("vibelign:"):
            commits.append(current)
        return commits[:n]
    except Exception:
        return []


def get_uncommitted_summary(root: Path) -> str | None:
    """Return a compact summary for currently uncommitted safe handoff paths."""
    return get_working_tree_summary(root)["summary"]


def get_work_memory_staleness_warning(root: Path) -> str | None:
    """Warn when watch/work memory is older than the latest git commit."""
    work_memory_path = MetaPaths(root).work_memory_path
    if not work_memory_path.exists():
        return None
    state = load_work_memory(work_memory_path)
    memory_time = _latest_watch_event_time(state)
    commit_time = _latest_commit_time(root)
    if memory_time is None or commit_time is None:
        return None
    if memory_time >= commit_time:
        return None
    return (
        "work_memory/watch data may be stale; trust git status, recent commits, "
        "explicit verification, and user-provided handoff summary first."
    )


def _latest_watch_event_time(state: WorkMemoryState) -> datetime | None:
    latest: datetime | None = None
    for event in state.get("recent_events", []) + state.get("warnings", []):
        parsed = _parse_timestamp(event.get("time", ""))
        if parsed is not None and (latest is None or parsed > latest):
            latest = parsed
    return latest


def _working_tree_numstat(root: Path) -> dict[str, str]:
    stats: dict[str, str] = {}
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotePath=false", "diff", "--numstat", "HEAD"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
    except Exception:
        return stats
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, removed, raw_path = parts[0], parts[1], parts[2]
        path = raw_path.split(" => ")[-1].strip("{}")
        if not should_include_handoff_path(path):
            continue
        stats[path] = "binary changed" if "-" in (added, removed) else f"+{added}/-{removed}"
    return stats


def _status_label(code: str) -> str:
    if "?" in code:
        return "untracked"
    if "A" in code:
        return "added"
    if "D" in code:
        return "deleted"
    if "R" in code:
        return "renamed"
    return "modified"


def _latest_commit_time(root: Path) -> datetime | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
    except Exception:
        return None
    return _parse_timestamp(result.stdout.strip())


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# === ANCHOR: TRANSFER_GIT_CONTEXT_GET_VERIFICATION_FRESHNESS_START ===
def get_verification_freshness(root: Path) -> str | None:
    """v2.0.37: 핸드오프 Verification snapshot 라벨용 freshness 판정.

    "fresh" iff state["verification_updated_at"] >= max(HEAD commit time, working tree dirty file mtime).
    "stale" iff verification 은 있는데 그 이후 git/working tree 변경 발생.
    None iff verification 기록 없음 (호출측에서 라벨 생략).
    """
    work_memory_path = MetaPaths(root).work_memory_path
    if not work_memory_path.exists():
        return None
    state = load_work_memory(work_memory_path)
    if not state.get("verification"):
        return None
    verification_time = _parse_timestamp(state.get("verification_updated_at", ""))
    if verification_time is None:
        return "stale"
    commit_time = _latest_commit_time(root)
    working_tree_time = _latest_dirty_file_mtime(root)
    benchmark = max(
        (t for t in (commit_time, working_tree_time) if t is not None),
        default=None,
    )
    if benchmark is None:
        return "fresh"
    return "fresh" if verification_time >= benchmark else "stale"
# === ANCHOR: TRANSFER_GIT_CONTEXT_GET_VERIFICATION_FRESHNESS_END ===


def _latest_dirty_file_mtime(root: Path) -> datetime | None:
    """git status 가 잡은 dirty 파일들의 최신 mtime."""
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotePath=false", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
    except Exception:
        return None
    latest: datetime | None = None
    for raw_line in result.stdout.splitlines():
        path_part = raw_line[3:].strip().split(" -> ")[-1].strip('"')
        if not path_part or not should_include_handoff_path(path_part):
            continue
        full = root / path_part
        try:
            mtime = full.stat().st_mtime
        except (FileNotFoundError, OSError):
            continue
        ts = datetime.fromtimestamp(mtime, tz=timezone.utc)
        if latest is None or ts > latest:
            latest = ts
    return latest


# === ANCHOR: TRANSFER_GIT_CONTEXT_END ===
