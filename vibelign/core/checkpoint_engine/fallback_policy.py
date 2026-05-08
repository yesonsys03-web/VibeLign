# === ANCHOR: CHECKPOINT_ENGINE_FALLBACK_POLICY_START ===
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import cast

from vibelign.core.meta_paths import MetaPaths

_ENV_FALLBACK_MARKERS = (
    "RUST_ENGINE_UNAVAILABLE",
    "RUST_ENGINE_INTEGRITY_FAILED",
    "RUST_ENGINE_STARTUP_FAILED",
    "RUST_ENGINE_PROCESS_FAILED",
)


def rust_disabled() -> bool:
    return os.environ.get("VIBELIGN_DISABLE_RUST_CHECKPOINT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def rust_required() -> bool:
    return os.environ.get("VIBELIGN_REQUIRE_RUST_CHECKPOINT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def engine_state_recording_disabled() -> bool:
    return os.environ.get("VIBELIGN_DISABLE_CHECKPOINT_ENGINE_STATE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def is_environment_fallback(reason: str | None) -> bool:
    if not reason:
        return False
    return any(marker in reason for marker in _ENV_FALLBACK_MARKERS)


def is_protocol_compatibility_fallback(reason: str | None) -> bool:
    if not reason:
        return False
    return "RUST_ENGINE_PROTOCOL_ERROR" in reason or "unknown variant" in reason


def record_engine_state(root: Path, engine_used: str, reason: str | None) -> None:
    if engine_state_recording_disabled():
        return
    state_path = MetaPaths(root).state_path
    state: dict[str, object] = {}
    try:
        if state_path.exists():
            loaded = cast(object, json.loads(state_path.read_text(encoding="utf-8")))
            if isinstance(loaded, dict):
                state = cast(dict[str, object], loaded)
    except (OSError, json.JSONDecodeError):
        state = {}
    state["engine_used"] = engine_used
    if reason:
        state["last_fallback_reason"] = reason
    elif engine_used == "rust":
        _ = state.pop("last_fallback_reason", None)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        _ = state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        print(f"[WARN] checkpoint engine state write failed: {exc}", file=sys.stderr)


# === ANCHOR: CHECKPOINT_ENGINE_FALLBACK_POLICY_END ===
