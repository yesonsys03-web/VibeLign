from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from vibelign.core.checkpoint_engine.router import inspect_backup_db
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import cli_print

print = cli_print


# === ANCHOR: VIB_BACKUP_DB_VIEWER_CMD_START ===
def _viewer_error_message(message: str) -> str:
    engine_markers = (
        "RUST_ENGINE_UNAVAILABLE",
        "RUST_ENGINE_INTEGRITY_FAILED",
        "RUST_ENGINE_STARTUP_FAILED",
        "RUST_ENGINE_PROCESS_FAILED",
        "RUST_ENGINE_INVALID_JSON",
    )
    if any(marker in message for marker in engine_markers) or "Rust backup DB viewer" in message:
        return "백업 관리 DB를 읽을 수 없어요. 설치된 앱/CLI의 백업 엔진을 확인해 주세요."
    if "locked" in message.lower() or "busy" in message.lower():
        return "다른 백업 작업이 끝난 뒤 다시 새로고침해 주세요."
    return f"백업 관리 DB를 읽을 수 없어요: {message}"


def run_vib_backup_db_viewer(args: Namespace) -> int:
    requested_root = Path(getattr(args, "root", ".")).resolve()
    root = resolve_project_root(requested_root)
    try:
        report = inspect_backup_db(root)
    except Exception as exc:
        message = _viewer_error_message(str(exc))
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
        else:
            print(message)
        return 1

    if getattr(args, "json", False):
        print(json.dumps({"ok": True, **report}, ensure_ascii=False))
    else:
        print("백업 관리 DB 상태를 확인했어요.")
    return 0


# === ANCHOR: VIB_BACKUP_DB_VIEWER_CMD_END ===
