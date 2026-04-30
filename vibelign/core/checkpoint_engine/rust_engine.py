# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_START ===
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from vibelign.core.local_checkpoints import CheckpointSummary
from vibelign.core.checkpoint_engine.requests import (
    checkpoint_create_request,
    checkpoint_diff_request,
    checkpoint_list_request,
    checkpoint_preview_request,
    checkpoint_prune_request,
    checkpoint_restore_files_request,
    checkpoint_restore_request,
    checkpoint_restore_suggestions_request,
    retention_apply_request,
)
from vibelign.core.checkpoint_engine.responses import (
    parse_checkpoint_create,
    parse_checkpoint_list,
    parse_diff,
    parse_preview,
    parse_prune,
    parse_restore,
    parse_restore_files,
    parse_retention,
    parse_suggestions,
)
from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS

_BACKUP_COMMAND_TIMEOUT_SECONDS = 90


@dataclass(frozen=True)
class RustEngineAvailability:
    available: bool
    binary_path: Path | None
    reason: str | None = None
    code: str | None = None


@dataclass(frozen=True)
class RustEngineResult:
    ok: bool
    payload: dict[str, object]
    error_code: str | None = None
    error_message: str | None = None


def _binary_name() -> str:
    return "vibelign-engine.exe" if sys.platform == "win32" else "vibelign-engine"


def _candidate_paths(root: Path) -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("VIBELIGN_ENGINE_PATH")
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(
        [
            root / "vibelign-core" / "target" / "debug" / _binary_name(),
            root / "vibelign-core" / "target" / "release" / _binary_name(),
            Path(__file__).resolve().parents[2] / "_bundled" / _binary_name(),
        ]
    )
    return candidates


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_integrity(binary_path: Path) -> str | None:
    manifest_path = binary_path.with_suffix(binary_path.suffix + ".sha256")
    if not manifest_path.exists():
        return "integrity manifest missing"
    expected = manifest_path.read_text(encoding="utf-8").split()[0].strip().lower()
    if not expected:
        return "integrity manifest empty"
    actual = _sha256(binary_path).lower()
    if actual != expected:
        return "integrity check failed"
    return None


def find_rust_engine(root: Path) -> RustEngineAvailability:
    for candidate in _candidate_paths(root):
        if not candidate.exists() or not candidate.is_file():
            continue
        integrity_error = _verify_integrity(candidate)
        if integrity_error:
            return RustEngineAvailability(
                False, candidate, integrity_error, "RUST_ENGINE_INTEGRITY_FAILED"
            )
        return RustEngineAvailability(True, candidate, None, None)
    return RustEngineAvailability(
        False, None, "rust engine binary missing", "RUST_ENGINE_UNAVAILABLE"
    )


def call_rust_engine(
    root: Path, request: dict[str, object], timeout_seconds: int = 30
) -> RustEngineResult:
    availability = find_rust_engine(root)
    if not availability.available or availability.binary_path is None:
        return RustEngineResult(
            ok=False,
            payload={},
            error_code=availability.code or "RUST_ENGINE_UNAVAILABLE",
            error_message=availability.reason or "rust engine unavailable",
        )
    try:
        completed = subprocess.run(
            [str(availability.binary_path)],
            input=json.dumps(request, ensure_ascii=False),
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as error:
        return RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_STARTUP_FAILED",
            error_message=str(error),
        )
    if completed.returncode != 0:
        return RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_PROCESS_FAILED",
            error_message=(completed.stderr or completed.stdout).strip(),
        )
    try:
        payload = cast(
            dict[str, object], json.loads((completed.stdout or "{}").strip() or "{}")
        )
    except json.JSONDecodeError as error:
        return RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_INVALID_JSON",
            error_message=str(error),
        )
    if payload.get("status") == "ok":
        return RustEngineResult(ok=True, payload=payload)
    return RustEngineResult(
        ok=False,
        payload=payload,
        error_code=str(payload.get("code", "RUST_ENGINE_ERROR")),
        error_message=str(payload.get("message", "rust engine error")),
    )


def create_checkpoint_with_rust(
    root: Path,
    message: str,
    *,
    trigger: str | None = None,
    git_commit_sha: str | None = None,
    git_commit_message: str | None = None,
) -> tuple[CheckpointSummary | None, str | None]:
    request = checkpoint_create_request(
        root,
        message,
        trigger=trigger,
        git_commit_sha=git_commit_sha,
        git_commit_message=git_commit_message,
    )
    result = call_rust_engine(
        root, request, timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS
    )
    return parse_checkpoint_create(result, message)


def list_checkpoints_with_rust(root: Path) -> tuple[list[CheckpointSummary] | None, str | None]:
    result = call_rust_engine(root, checkpoint_list_request(root))
    return parse_checkpoint_list(result)


def restore_checkpoint_with_rust(root: Path, checkpoint_id: str) -> tuple[bool, str | None]:
    result = call_rust_engine(
        root,
        checkpoint_restore_request(root, checkpoint_id),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_restore(result)


def diff_checkpoints_with_rust(
    root: Path, from_checkpoint_id: str, to_checkpoint_id: str
) -> tuple[dict[str, object] | None, str | None]:
    result = call_rust_engine(
        root,
        checkpoint_diff_request(root, from_checkpoint_id, to_checkpoint_id),
    )
    return parse_diff(result)


def preview_restore_with_rust(
    root: Path, checkpoint_id: str, relative_paths: list[str] | None = None
) -> tuple[dict[str, object] | None, str | None]:
    request = checkpoint_preview_request(root, checkpoint_id, relative_paths)
    result = call_rust_engine(
        root, request, timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS
    )
    return parse_preview(result)


def restore_files_with_rust(
    root: Path, checkpoint_id: str, relative_paths: list[str]
) -> tuple[int | None, str | None]:
    result = call_rust_engine(
        root,
        checkpoint_restore_files_request(root, checkpoint_id, relative_paths),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_restore_files(result)


def restore_suggestions_with_rust(
    root: Path, checkpoint_id: str, cap: int = 5
) -> tuple[dict[str, object] | None, str | None]:
    result = call_rust_engine(
        root,
        checkpoint_restore_suggestions_request(root, checkpoint_id, cap),
    )
    return parse_suggestions(result)


def prune_checkpoints_with_rust(
    root: Path, keep_latest: int = 30
) -> tuple[dict[str, int] | None, str | None]:
    result = call_rust_engine(
        root,
        checkpoint_prune_request(root, keep_latest),
    )
    return parse_prune(result)


def apply_retention_with_rust(root: Path) -> tuple[dict[str, object] | None, str | None]:
    result = call_rust_engine(
        root,
        retention_apply_request(root),
        timeout_seconds=_BACKUP_COMMAND_TIMEOUT_SECONDS,
    )
    return parse_retention(result)


# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_END ===
