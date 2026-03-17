import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, cast

from vibelign.core.meta_paths import MetaPaths


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    ".sisyphus",
}

IGNORED_FILES = {
    "VIBELIGN_PATCH_REQUEST.md",
    "VIBELIGN_EXPLAIN.md",
    "VIBELIGN_GUARD.md",
    "VIBELIGN_ASK.md",
}


@dataclass
class CheckpointSummary:
    checkpoint_id: str
    created_at: str
    message: str
    file_count: int
    total_size_bytes: int = 0
    pinned: bool = False
    pruned_count: int = 0
    pruned_bytes: int = 0


@dataclass
class RetentionPolicy:
    keep_latest: int = 30
    keep_daily_days: int = 14
    keep_weekly_weeks: int = 8
    max_total_size_bytes: int = 2 * 1024 * 1024 * 1024
    max_age_days: int = 180
    min_keep: int = 10


DEFAULT_RETENTION_POLICY = RetentionPolicy()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _should_skip_dir(path: Path, meta: MetaPaths) -> bool:
    parts = path.parts
    if any(part in IGNORED_DIRS for part in parts):
        return True
    try:
        if path.resolve().is_relative_to(meta.checkpoints_dir.resolve()):
            return True
        if path.resolve().is_relative_to(meta.reports_dir.resolve()):
            return True
    except Exception:
        pass
    return False


def iter_snapshot_files(root: Path) -> Iterable[Path]:
    meta = MetaPaths(root)
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if path.name in IGNORED_FILES:
            continue
        if _should_skip_dir(path, meta):
            continue
        yield path


def _manifest_path(snapshot_dir: Path) -> Path:
    return snapshot_dir / "manifest.json"


def _files_dir(snapshot_dir: Path) -> Path:
    return snapshot_dir / "files"


def _current_file_map(root: Path) -> Dict[str, Dict[str, object]]:
    mapping: Dict[str, Dict[str, object]] = {}
    for path in iter_snapshot_files(root):
        rel = str(path.relative_to(root))
        mapping[rel] = {
            "path": rel,
            "sha256": _sha256(path),
            "size": path.stat().st_size,
        }
    return mapping


def _load_manifest(snapshot_dir: Path) -> Optional[Dict[str, object]]:
    manifest_path = _manifest_path(snapshot_dir)
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _manifest_files(manifest: Dict[str, object]) -> List[Dict[str, object]]:
    raw_files = manifest.get("files", [])
    if not isinstance(raw_files, list):
        return []
    return [item for item in raw_files if isinstance(item, dict)]


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _parse_checkpoint_time(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def friendly_time(created_at: str) -> str:
    """타임스탬프를 사람이 읽기 쉬운 한국어 형태로 변환."""
    cp_time = _parse_checkpoint_time(created_at)
    if cp_time is None:
        return created_at
    local_time = cp_time.astimezone()
    now = datetime.now(timezone.utc).astimezone()
    delta = now - local_time
    time_str = local_time.strftime("%H:%M:%S")
    if delta.days == 0:
        return f"오늘 {time_str}"
    elif delta.days == 1:
        return f"어제 {time_str}"
    elif delta.days < 7:
        days = ["월", "화", "수", "목", "금", "토", "일"]
        day_name = days[local_time.weekday()]
        return f"{local_time.month}월 {local_time.day}일({day_name}) {time_str}"
    else:
        return f"{local_time.month}월 {local_time.day}일 {time_str}"


def list_checkpoints(root: Path) -> List[CheckpointSummary]:
    meta = MetaPaths(root)
    if not meta.checkpoints_dir.exists():
        return []
    summaries: List[CheckpointSummary] = []
    for snapshot_dir in sorted(meta.checkpoints_dir.iterdir(), reverse=True):
        if not snapshot_dir.is_dir():
            continue
        manifest = _load_manifest(snapshot_dir)
        if not isinstance(manifest, dict):
            continue
        summaries.append(
            CheckpointSummary(
                checkpoint_id=str(manifest.get("id", snapshot_dir.name)),
                created_at=str(manifest.get("created_at", snapshot_dir.name)),
                message=str(manifest.get("message", "")),
                file_count=_coerce_int(manifest.get("file_count", 0)),
                total_size_bytes=_coerce_int(manifest.get("total_size_bytes", 0)),
                pinned=bool(manifest.get("pinned", False)),
            )
        )
    return summaries


def _latest_manifest(root: Path) -> Optional[Dict[str, object]]:
    checkpoints = list_checkpoints(root)
    if not checkpoints:
        return None
    meta = MetaPaths(root)
    return _load_manifest(meta.checkpoints_dir / checkpoints[0].checkpoint_id)


def _manifest_file_map(manifest: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    files = _manifest_files(manifest)
    return {str(item["path"]): item for item in files if "path" in item}


def create_checkpoint(root: Path, message: str) -> Optional[CheckpointSummary]:
    meta = MetaPaths(root)
    meta.ensure_vibelign_dirs()
    current_files = _current_file_map(root)
    latest = _latest_manifest(root)
    latest_files = {}
    if isinstance(latest, dict):
        latest_files = _manifest_file_map(latest)
    if current_files == latest_files:
        return None
    checkpoint_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot_dir = meta.checkpoints_dir / checkpoint_id
    files_dir = _files_dir(snapshot_dir)
    files_dir.mkdir(parents=True, exist_ok=True)
    for rel in current_files:
        src = root / rel
        dst = files_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    manifest = {
        "schema_version": 1,
        "id": checkpoint_id,
        "created_at": checkpoint_id,
        "message": message,
        "pinned": False,
        "file_count": len(current_files),
        "total_size_bytes": sum(
            cast(int, item["size"]) for item in current_files.values()
        ),
        "files": sorted(current_files.values(), key=lambda item: str(item["path"])),
    }
    _ = _manifest_path(snapshot_dir).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = CheckpointSummary(
        checkpoint_id=checkpoint_id,
        created_at=checkpoint_id,
        message=message,
        file_count=len(current_files),
        total_size_bytes=_coerce_int(manifest["total_size_bytes"]),
        pinned=False,
    )
    pruned = prune_checkpoints(root)
    summary.pruned_count = pruned["count"]
    summary.pruned_bytes = pruned["bytes"]
    return summary


def has_changes_since_checkpoint(root: Path, checkpoint_id: str) -> bool:
    meta = MetaPaths(root)
    manifest = _load_manifest(meta.checkpoints_dir / checkpoint_id)
    if not isinstance(manifest, dict):
        return True
    return _current_file_map(root) != _manifest_file_map(manifest)


def restore_checkpoint(root: Path, checkpoint_id: str) -> bool:
    meta = MetaPaths(root)
    snapshot_dir = meta.checkpoints_dir / checkpoint_id
    manifest = _load_manifest(snapshot_dir)
    if not isinstance(manifest, dict):
        return False
    files = _manifest_files(manifest)
    snapshot_files = {str(item["path"]) for item in files if "path" in item}
    current_files = {str(path.relative_to(root)) for path in iter_snapshot_files(root)}
    for rel in sorted(current_files - snapshot_files, reverse=True):
        target = root / rel
        if target.exists():
            target.unlink()
            parent = target.parent
            while parent != root and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    files_dir = _files_dir(snapshot_dir)
    for rel in sorted(snapshot_files):
        src = files_dir / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return True


def prune_checkpoints(
    root: Path, policy: RetentionPolicy = DEFAULT_RETENTION_POLICY
) -> Dict[str, int]:
    checkpoints = list_checkpoints(root)
    now = datetime.now(timezone.utc)
    has_old_checkpoint = any(
        (_parse_checkpoint_time(cp.created_at) or now)
        < now - timedelta(days=policy.max_age_days)
        for cp in checkpoints
    )
    if (
        len(checkpoints) <= policy.keep_latest
        and sum(cp.total_size_bytes for cp in checkpoints)
        <= policy.max_total_size_bytes
        and not has_old_checkpoint
    ):
        return {"count": 0, "bytes": 0}

    protected_ids: Set[str] = set()
    protected_ids.update(cp.checkpoint_id for cp in checkpoints[: policy.keep_latest])

    seen_days: Set[str] = set()
    seen_weeks: Set[str] = set()
    for cp in checkpoints:
        cp_time = _parse_checkpoint_time(cp.created_at)
        if cp.pinned:
            protected_ids.add(cp.checkpoint_id)
            continue
        if cp_time is None:
            continue
        age = now - cp_time
        if age <= timedelta(days=policy.keep_daily_days):
            day_key = cp_time.strftime("%Y-%m-%d")
            if day_key not in seen_days:
                seen_days.add(day_key)
                protected_ids.add(cp.checkpoint_id)
        elif age <= timedelta(weeks=policy.keep_weekly_weeks):
            week_key = cp_time.strftime("%Y-W%W")
            if week_key not in seen_weeks:
                seen_weeks.add(week_key)
                protected_ids.add(cp.checkpoint_id)

    total_size = sum(cp.total_size_bytes for cp in checkpoints)
    deleted_count = 0
    deleted_bytes = 0
    kept = list(checkpoints)
    min_keep = min(policy.min_keep, len(checkpoints))
    meta = MetaPaths(root)

    for cp in reversed(checkpoints):
        if len(kept) <= min_keep:
            break
        cp_time = _parse_checkpoint_time(cp.created_at)
        too_old = cp_time is not None and cp_time < now - timedelta(
            days=policy.max_age_days
        )
        over_size = total_size > policy.max_total_size_bytes
        if cp.checkpoint_id in protected_ids and not too_old:
            continue
        if not over_size and not too_old and len(kept) <= policy.keep_latest:
            continue
        snapshot_dir = meta.checkpoints_dir / cp.checkpoint_id
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
        deleted_count += 1
        deleted_bytes += cp.total_size_bytes
        total_size -= cp.total_size_bytes
        kept = [item for item in kept if item.checkpoint_id != cp.checkpoint_id]

    return {"count": deleted_count, "bytes": deleted_bytes}
