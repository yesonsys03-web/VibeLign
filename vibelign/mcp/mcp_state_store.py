# === ANCHOR: MCP_STATE_STORE_START ===
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import cast

from vibelign.core.meta_paths import MetaPaths

PATCH_SESSION_KEY = "patch_session"
PLANNING_KEY = "planning"


# === ANCHOR: MCP_STATE_STORE_LOAD_STATE_START ===
def load_state(meta: MetaPaths) -> dict[str, object]:
    if not meta.state_path.exists():
        return {}
    try:
        raw_state = cast(
            object, json.loads(meta.state_path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    if not isinstance(raw_state, dict):
        return {}
    return {
        str(key): value for key, value in cast(dict[object, object], raw_state).items()
    }


# === ANCHOR: MCP_STATE_STORE_LOAD_STATE_END ===


# === ANCHOR: MCP_STATE_STORE_SAVE_STATE_START ===
def save_state(meta: MetaPaths, state: dict[str, object]) -> None:
    meta.ensure_vibelign_dirs()
    _ = meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# === ANCHOR: MCP_STATE_STORE_SAVE_STATE_END ===


# === ANCHOR: MCP_STATE_STORE_LOAD_PATCH_SESSION_START ===
def load_patch_session(meta: MetaPaths) -> dict[str, object] | None:
    state = load_state(meta)
    session = state.get(PATCH_SESSION_KEY)
    if not isinstance(session, dict):
        return None
    return {
        str(key): value for key, value in cast(dict[object, object], session).items()
    }


# === ANCHOR: MCP_STATE_STORE_LOAD_PATCH_SESSION_END ===


# === ANCHOR: MCP_STATE_STORE_SAVE_PATCH_SESSION_START ===
def save_patch_session(meta: MetaPaths, session: dict[str, object] | None) -> None:
    state = load_state(meta)
    if session is None:
        _ = state.pop(PATCH_SESSION_KEY, None)
    else:
        state[PATCH_SESSION_KEY] = session
    save_state(meta, state)


# === ANCHOR: MCP_STATE_STORE_SAVE_PATCH_SESSION_END ===


# === ANCHOR: MCP_STATE_STORE_LOAD_PLANNING_SESSION_START ===
def load_planning_session(meta: MetaPaths) -> dict[str, object] | None:
    state = load_state(meta)
    planning = state.get(PLANNING_KEY)
    if not isinstance(planning, dict):
        return None
    return {
        str(key): value for key, value in cast(dict[object, object], planning).items()
    }


# === ANCHOR: MCP_STATE_STORE_LOAD_PLANNING_SESSION_END ===


# === ANCHOR: MCP_STATE_STORE_SAVE_PLANNING_SESSION_START ===
def save_planning_session(meta: MetaPaths, planning: dict[str, object] | None) -> None:
    state = load_state(meta)
    if planning is None:
        _ = state.pop(PLANNING_KEY, None)
    else:
        state[PLANNING_KEY] = planning
    save_state(meta, state)


# === ANCHOR: MCP_STATE_STORE_SAVE_PLANNING_SESSION_END ===


# === ANCHOR: MCP_STATE_STORE_PATCH_SESSION_NOW_START ===
def patch_session_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# === ANCHOR: MCP_STATE_STORE_PATCH_SESSION_NOW_END ===


# === ANCHOR: MCP_STATE_STORE_NEW_PATCH_SESSION_ID_START ===
def new_patch_session_id() -> str:
    return uuid.uuid4().hex


# === ANCHOR: MCP_STATE_STORE_NEW_PATCH_SESSION_ID_END ===
# === ANCHOR: MCP_STATE_STORE_END ===
