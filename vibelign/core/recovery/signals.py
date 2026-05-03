# === ANCHOR: RECOVERY_SIGNALS_START ===
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from vibelign.core.checkpoint_engine.router import (
    has_changes_since_checkpoint,
    list_checkpoints,
    preview_restore,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import load_project_map
from vibelign.core.work_memory import WorkMemoryState, load_work_memory

from .models import RecoverySignalSet, SafeCheckpointCandidate


# === ANCHOR: RECOVERY_SIGNALS__COLLECT_BASIC_SIGNALS_START ===
def collect_basic_signals(project_root: Path) -> RecoverySignalSet:
    changed_paths = _filter_recovery_paths(
        [
            *_git_paths(project_root, ["diff", "--name-only"]),
            *_git_paths(project_root, ["diff", "--cached", "--name-only"]),
        ]
    )
    untracked_paths = _filter_recovery_paths(_git_untracked_status_paths(project_root))
    meta = MetaPaths(project_root)
    work_memory = load_work_memory(meta.work_memory_path)
    explicit_relevant_paths = _filter_recovery_paths(
        [
            entry.get("path", "")
            for entry in work_memory.get("relevant_files", [])
            if entry.get("source") == "explicit"
        ]
    )
    recent_patch_paths = _filter_recovery_paths(_recent_work_memory_paths(work_memory))
    all_paths = [*changed_paths, *untracked_paths, *explicit_relevant_paths, *recent_patch_paths]
    project_map_categories, anchor_intents_by_path = _project_context(project_root, all_paths)
    guard_summary, guard_has_failures = _guard_report_summary(meta)
    return RecoverySignalSet(
        changed_paths=changed_paths,
        untracked_paths=untracked_paths,
        explicit_relevant_paths=explicit_relevant_paths,
        recent_patch_paths=recent_patch_paths,
        project_map_categories=project_map_categories,
        anchor_intents_by_path=anchor_intents_by_path,
        safe_checkpoint_candidate=_latest_safe_checkpoint(project_root),
        guard_has_failures=guard_has_failures,
        guard_summary=guard_summary,
        explain_summary=_explain_report_summary(meta),
    )
# === ANCHOR: RECOVERY_SIGNALS__COLLECT_BASIC_SIGNALS_END ===


def _git_paths(project_root: Path, args: list[str]) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]


def _recent_work_memory_paths(work_memory: WorkMemoryState) -> list[str]:
    paths: list[str] = []
    for entry in work_memory.get("relevant_files", []):
        if entry.get("source") == "watch":
            paths.append(str(entry.get("path", "")))
    for event in work_memory.get("recent_events", []):
        if event.get("kind") not in {"checkpoint", "commit"}:
            paths.append(str(event.get("path", "")))
    return paths


def _git_untracked_status_paths(project_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--short", "--untracked-files=normal"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if line.startswith("?? "):
            paths.append(line[3:].strip().replace("\\", "/"))
    return paths


def _filter_recovery_paths(paths: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for path in paths:
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        if not parts or _is_generated_path(parts):
            continue
        normalized = "/".join(parts)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _is_generated_path(parts: list[str]) -> bool:
    excluded = {
        ".git",
        ".hg",
        ".svn",
        ".vibelign",
        ".venv",
        "node_modules",
        "dist",
        "build",
        "target",
        ".next",
        "__pycache__",
        "coverage",
        "out",
        "bin",
        "obj",
    }
    return any(part.lower() in excluded for part in parts)


def _latest_safe_checkpoint(project_root: Path) -> SafeCheckpointCandidate | None:
    with _checkpoint_engine_read_only_mode():
        try:
            checkpoints = list_checkpoints(project_root)
        except Exception:
            return None
        if not checkpoints:
            return None
        latest = checkpoints[0]
        if not latest.checkpoint_id or not latest.created_at:
            return None
        try:
            predates_change = has_changes_since_checkpoint(project_root, latest.checkpoint_id)
        except Exception:
            predates_change = False
        try:
            preview_data = preview_restore(project_root, latest.checkpoint_id, None)
        except Exception:
            preview_data = {}
    preview_available = bool(preview_data) and preview_data.get("ok", True) is not False
    metadata_complete = bool(latest.file_count and latest.file_count > 0)
    if not (metadata_complete and preview_available and predates_change):
        return None
    return SafeCheckpointCandidate(
        checkpoint_id=latest.checkpoint_id,
        created_at=latest.created_at,
        message=latest.message,
        metadata_complete=metadata_complete,
        preview_available=preview_available,
        predates_change=predates_change,
    )


@contextmanager
def _checkpoint_engine_read_only_mode() -> Iterator[None]:
    key = "VIBELIGN_DISABLE_CHECKPOINT_ENGINE_STATE"
    previous = os.environ.get(key)
    os.environ[key] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def _project_context(project_root: Path, paths: list[str]) -> tuple[dict[str, str], dict[str, list[str]]]:
    snapshot, _error = load_project_map(project_root)
    if snapshot is None:
        return {}, {}
    anchor_meta = _load_anchor_meta(MetaPaths(project_root))
    categories: dict[str, str] = {}
    anchor_intents_by_path: dict[str, list[str]] = {}
    for path in paths:
        category = snapshot.classify_path(path)
        if category:
            categories[path] = category
        file_entry = snapshot.files.get(path, {})
        anchors = file_entry.get("anchors") if isinstance(file_entry, dict) else None
        intents = _anchor_intents(anchors, anchor_meta)
        if intents:
            anchor_intents_by_path[path] = intents
    return categories, anchor_intents_by_path


def _load_anchor_meta(meta: MetaPaths) -> dict[str, dict[str, object]]:
    if not meta.anchor_meta_path.exists():
        return {}
    try:
        loaded = json.loads(meta.anchor_meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {
        str(key): cast(dict[str, object], value)
        for key, value in cast(dict[object, object], loaded).items()
        if isinstance(value, dict)
    }


def _anchor_intents(anchors: object, anchor_meta: dict[str, dict[str, object]]) -> list[str]:
    if not isinstance(anchors, list):
        return []
    intents: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        if not isinstance(anchor, str):
            continue
        meta = anchor_meta.get(anchor, {})
        raw_intent = meta.get("intent", "")
        if not isinstance(raw_intent, str):
            continue
        intent = " ".join(raw_intent.split())
        if intent and intent not in seen:
            seen.add(intent)
            intents.append(intent)
    return intents


def _guard_report_summary(meta: MetaPaths) -> tuple[str, bool]:
    report_path = meta.report_path("guard", "json")
    if not report_path.exists():
        return "", False
    try:
        loaded = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return "", False
    data = _report_data(loaded)
    summary = _short_text(data.get("summary"))
    status = _short_text(data.get("status")).lower()
    blocked = data.get("blocked") is True
    risk = _short_text(data.get("change_risk_level")).lower()
    return summary, blocked or status == "fail" or risk == "high"


def _explain_report_summary(meta: MetaPaths) -> str:
    report_path = meta.report_path("explain", "json")
    if not report_path.exists():
        return ""
    try:
        loaded = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ""
    return _short_text(_report_data(loaded).get("summary"))


def _report_data(loaded: object) -> dict[str, object]:
    if not isinstance(loaded, dict):
        return {}
    raw_data = cast(dict[object, object], loaded).get("data", loaded)
    if not isinstance(raw_data, dict):
        return {}
    return cast(dict[str, object], raw_data)


def _short_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:240]

# === ANCHOR: RECOVERY_SIGNALS_END ===
