# === ANCHOR: VIB_LOG_GUI_ERROR_CMD_START ===
from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import cast

from vibelign.core.error_log import record_gui_error
from vibelign.core.project_root import resolve_project_root


def run_vib_log_gui_error(args: Namespace) -> None:
    if not bool(getattr(args, "batch", False)):
        return
    root_arg = getattr(args, "root", None)
    root = resolve_project_root(Path(str(root_arg))) if isinstance(root_arg, str) and root_arg else resolve_project_root(Path.cwd())
    try:
        payload = cast(object, json.loads(sys.stdin.read() or "[]"))
    except json.JSONDecodeError:
        return
    if not isinstance(payload, list):
        return
    items = cast(list[object], payload)
    for item in items:
        if isinstance(item, dict):
            record_gui_error(root, _string_key_dict(cast(dict[object, object], item)))


def _string_key_dict(value: dict[object, object]) -> dict[str, object]:
    return {str(key): item for key, item in value.items()}
# === ANCHOR: VIB_LOG_GUI_ERROR_CMD_END ===
