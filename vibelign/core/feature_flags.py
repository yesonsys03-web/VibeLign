# === ANCHOR: FEATURE_FLAGS_START ===
"""Feature flag 관리.

환경변수로 제어:
  VIBELIGN_USE_ACTION_ENGINE=true   Action Engine 활성화
  VIBELIGN_DISABLE_RUST_CHECKPOINT=true   Roll back checkpoint engine to Python
"""
from __future__ import annotations

import os

_FLAG_ENV_MAP = {
    "USE_ACTION_ENGINE": "VIBELIGN_USE_ACTION_ENGINE",
    "DISABLE_RUST_CHECKPOINT": "VIBELIGN_DISABLE_RUST_CHECKPOINT",
}


def is_enabled(flag: str) -> bool:
    """flag가 활성화되어 있으면 True 반환."""
    env_var = _FLAG_ENV_MAP.get(flag)
    if env_var is None:
        return False
    return os.environ.get(env_var, "").strip().lower() in {"1", "true", "yes"}
# === ANCHOR: FEATURE_FLAGS_END ===
