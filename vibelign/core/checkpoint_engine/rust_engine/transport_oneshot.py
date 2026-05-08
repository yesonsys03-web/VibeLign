# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_TRANSPORT_ONESHOT_START ===
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from vibelign.core.checkpoint_engine.rust_engine.discovery import find_rust_engine
from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS


@dataclass(frozen=True)
class RustEngineResult:
    ok: bool
    payload: dict[str, object]
    error_code: str | None = None
    error_message: str | None = None


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
        # Callers are expected to pass a platform-normalized project root. In particular,
        # Windows `\\?\` UNC-prefixed cwd values are rejected by CreateProcess.
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


# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_TRANSPORT_ONESHOT_END ===
