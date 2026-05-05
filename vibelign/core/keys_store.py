# === ANCHOR: KEYS_STORE_START ===
"""플랫폼별 API 키 파일을 읽고 쓰는 단일 저장소.

- macOS/Linux: ~/.config/vibelign/api_keys.json
- Windows:     %APPDATA%\\vibelign\\api_keys.json

우선순위: disabled override > keys file > os.environ
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
_DISABLED_KEYS_FIELD = "__disabled_keys"


def _load_raw() -> dict[str, object]:
    path = keys_file_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _disabled_keys(data: dict[str, object] | None = None) -> set[str]:
    raw = _load_raw() if data is None else data
    disabled = raw.get(_DISABLED_KEYS_FIELD)
    if not isinstance(disabled, list):
        return set()
    return {str(item) for item in disabled if item}


def _write_raw(data: dict[str, object]) -> None:
    path = keys_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


# === ANCHOR: KEYS_STORE__KEYS_FILE_PATH_START ===
def _keys_file_path_for_platform(os_name: str, appdata: str | None, xdg: str | None, home: str) -> Path:
    if os_name == "nt":
        config_root = appdata or str(Path(home) / "AppData" / "Roaming")
        return Path(config_root) / "vibelign" / "api_keys.json"
    config_root = xdg or str(Path(home) / ".config")
    return Path(config_root) / "vibelign" / "api_keys.json"


def keys_file_path() -> Path:
    return _keys_file_path_for_platform(
        os.name,
        os.environ.get("APPDATA"),
        os.environ.get("XDG_CONFIG_HOME"),
        str(Path.home()),
    )
# === ANCHOR: KEYS_STORE__KEYS_FILE_PATH_END ===


# === ANCHOR: KEYS_STORE__LOAD_START ===
def load_keys() -> dict[str, str]:
    """파일에서 키 맵을 읽어 반환. 파일이 없거나 파싱 실패 시 빈 dict."""
    data = _load_raw()
    disabled = _disabled_keys(data)
    return {
        str(k): v
        for k, v in data.items()
        if isinstance(v, str) and v and str(k) not in disabled
    }
# === ANCHOR: KEYS_STORE__LOAD_END ===


# === ANCHOR: KEYS_STORE__SAVE_START ===
def save_key(key_name: str, value: str) -> None:
    """단일 키를 파일에 저장(upsert). 빈 값이면 삭제."""
    data = _load_raw()
    disabled = _disabled_keys(data)
    if value:
        data[key_name] = value
        disabled.discard(key_name)
    else:
        data.pop(key_name, None)
        disabled.add(key_name)
    if disabled:
        data[_DISABLED_KEYS_FIELD] = sorted(disabled)
    else:
        data.pop(_DISABLED_KEYS_FIELD, None)
    _write_raw(data)
# === ANCHOR: KEYS_STORE__SAVE_END ===


# === ANCHOR: KEYS_STORE__DELETE_START ===
def delete_key(key_name: str) -> None:
    save_key(key_name, "")
# === ANCHOR: KEYS_STORE__DELETE_END ===


# === ANCHOR: KEYS_STORE__GET_KEY_START ===
def get_key(key_name: str) -> str | None:
    """삭제 override가 없으면 VibeLign 저장 키 우선, 없으면 환경변수를 읽는다."""
    if is_key_disabled(key_name):
        return None
    stored = load_keys().get(key_name)
    if stored:
        return stored
    val = os.environ.get(key_name)
    if val:
        return val
    return None
# === ANCHOR: KEYS_STORE__GET_KEY_END ===


def is_key_disabled(key_name: str) -> bool:
    return key_name in _disabled_keys()


# === ANCHOR: KEYS_STORE__HAS_ANY_AI_KEY_START ===
def has_any_ai_key() -> bool:
    """환경변수 또는 파일에 AI API 키가 하나라도 있으면 True."""
    return any(get_key(k) for k in _AI_KEY_NAMES)
# === ANCHOR: KEYS_STORE__HAS_ANY_AI_KEY_END ===

# === ANCHOR: KEYS_STORE_END ===
