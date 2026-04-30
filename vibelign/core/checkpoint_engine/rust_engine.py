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
from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS


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
    request: dict[str, object] = {
        "command": "checkpoint_create",
        "root": str(root),
        "message": message,
    }
    if trigger is not None:
        request["trigger"] = trigger
    if git_commit_sha is not None:
        request["git_commit_sha"] = git_commit_sha
    if git_commit_message is not None:
        request["git_commit_message"] = git_commit_message
    result = call_rust_engine(
        root, request
    )
    if not result.ok:
        return None, _format_error(result, "rust checkpoint failed")
    result_kind = result.payload.get("result")
    if result_kind == "no_changes":
        return None, None
    if result_kind != "created":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected checkpoint create result"
    summary = _summary_from_payload(result.payload, fallback_message=message)
    if summary is None:
        return None, "RUST_ENGINE_PROTOCOL_ERROR: created response missing checkpoint_id"
    return summary, None


def list_checkpoints_with_rust(root: Path) -> tuple[list[CheckpointSummary] | None, str | None]:
    result = call_rust_engine(root, {"command": "checkpoint_list", "root": str(root)})
    if not result.ok:
        return None, _format_error(result, "rust checkpoint list failed")
    raw_checkpoints = result.payload.get("checkpoints")
    if not isinstance(raw_checkpoints, list):
        return None, "RUST_ENGINE_PROTOCOL_ERROR: list response missing checkpoints"
    summaries: list[CheckpointSummary] = []
    for raw_item in cast(list[object], raw_checkpoints):
        if isinstance(raw_item, dict):
            summary = _summary_from_payload(cast(dict[str, object], raw_item))
            if summary is not None:
                summaries.append(summary)
    return summaries, None


def restore_checkpoint_with_rust(root: Path, checkpoint_id: str) -> tuple[bool, str | None]:
    result = call_rust_engine(
        root,
        {
            "command": "checkpoint_restore",
            "root": str(root),
            "checkpoint_id": checkpoint_id,
        },
    )
    if not result.ok:
        return False, _format_error(result, "rust checkpoint restore failed")
    return True, None


def prune_checkpoints_with_rust(
    root: Path, keep_latest: int = 30
) -> tuple[dict[str, int] | None, str | None]:
    result = call_rust_engine(
        root,
        {"command": "checkpoint_prune", "root": str(root), "keep_latest": keep_latest},
    )
    if not result.ok:
        return None, _format_error(result, "rust checkpoint prune failed")
    if "pruned_count" not in result.payload or "pruned_bytes" not in result.payload:
        return None, "RUST_ENGINE_PROTOCOL_ERROR: prune response missing counts"
    return {
        "count": _coerce_int(result.payload.get("pruned_count", 0)),
        "bytes": _coerce_int(result.payload.get("pruned_bytes", 0)),
    }, None


def _summary_from_payload(
    payload: dict[str, object], fallback_message: str = ""
) -> CheckpointSummary | None:
    checkpoint_id = payload.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        return None
    return CheckpointSummary(
        checkpoint_id=checkpoint_id,
        created_at=str(payload.get("created_at", checkpoint_id)),
        message=str(payload.get("message", fallback_message)),
        file_count=_coerce_int(payload.get("file_count", 0)),
        total_size_bytes=_coerce_int(payload.get("total_size_bytes", 0)),
        pinned=bool(payload.get("pinned", False)),
    )


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


def _format_error(result: RustEngineResult, fallback: str) -> str:
    code = result.error_code or "RUST_ENGINE_ERROR"
    message = result.error_message or fallback
    return f"{code}: {message}"


# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_END ===
