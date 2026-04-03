# === ANCHOR: KEYS_STORE_START ===
"""플랫폼별 API 키 파일을 읽고 쓰는 단일 저장소.

- macOS/Linux: ~/.config/vibelign/api_keys.json
- Windows:     %APPDATA%\\vibelign\\api_keys.json

우선순위: os.environ > keys file
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_AI_KEY_NAMES = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GLM_API_KEY",
    "MOONSHOT_API_KEY",
]


# === ANCHOR: KEYS_STORE__KEYS_FILE_PATH_START ===
def keys_file_path() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "vibelign" / "api_keys.json"
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / "vibelign" / "api_keys.json"
# === ANCHOR: KEYS_STORE__KEYS_FILE_PATH_END ===


# === ANCHOR: KEYS_STORE__LOAD_START ===
def load_keys() -> dict[str, str]:
    """파일에서 키 맵을 읽어 반환. 파일이 없거나 파싱 실패 시 빈 dict."""
    path = keys_file_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if v}
    except Exception:
        return {}
# === ANCHOR: KEYS_STORE__LOAD_END ===


# === ANCHOR: KEYS_STORE__SAVE_START ===
def save_key(key_name: str, value: str) -> None:
    """단일 키를 파일에 저장(upsert). 빈 값이면 삭제."""
    path = keys_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_keys()
    if value:
        data[key_name] = value
    else:
        data.pop(key_name, None)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
# === ANCHOR: KEYS_STORE__SAVE_END ===


# === ANCHOR: KEYS_STORE__DELETE_START ===
def delete_key(key_name: str) -> None:
    save_key(key_name, "")
# === ANCHOR: KEYS_STORE__DELETE_END ===


# === ANCHOR: KEYS_STORE__GET_KEY_START ===
def get_key(key_name: str) -> str | None:
    """환경변수 우선, 없으면 파일에서 읽는다."""
    val = os.environ.get(key_name)
    if val:
        return val
    return load_keys().get(key_name)
# === ANCHOR: KEYS_STORE__GET_KEY_END ===


# === ANCHOR: KEYS_STORE__HAS_ANY_AI_KEY_START ===
def has_any_ai_key() -> bool:
    """환경변수 또는 파일에 AI API 키가 하나라도 있으면 True."""
    stored = load_keys()
    return any(os.environ.get(k) or stored.get(k) for k in _AI_KEY_NAMES)
# === ANCHOR: KEYS_STORE__HAS_ANY_AI_KEY_END ===

# === ANCHOR: KEYS_STORE_END ===
