from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from vibelign.core.checkpoint_engine.router import apply_retention, maintain_backup_db
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import cli_print

print = cli_print


# === ANCHOR: VIB_BACKUP_CLEANUP_CMD_START ===
def _cleanup_error_message(message: str) -> str:
    engine_markers = (
        "RUST_ENGINE_UNAVAILABLE",
        "RUST_ENGINE_INTEGRITY_FAILED",
        "RUST_ENGINE_STARTUP_FAILED",
        "RUST_ENGINE_PROCESS_FAILED",
        "RUST_ENGINE_INVALID_JSON",
    )
    if any(marker in message for marker in engine_markers):
        return "백업 정리를 실행할 수 없어요. 설치된 앱/CLI의 백업 엔진을 확인해 주세요."
    if "locked" in message.lower() or "busy" in message.lower():
        return "다른 백업 작업이 끝난 뒤 다시 실행해 주세요."
    return f"백업 정리를 실행할 수 없어요: {message}"


def run_vib_backup_cleanup(args: Namespace) -> int:
    requested_root = Path(getattr(args, "root", ".")).resolve()
    root = resolve_project_root(requested_root)
    try:
        retention = apply_retention(root)
        maintenance = maintain_backup_db(root, apply=True)
    except Exception as exc:
        message = _cleanup_error_message(str(exc))
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
        else:
            print(message)
        return 1

    payload = {
        "ok": True,
        "result": "backup_cleanup",
        "retention": retention,
        "maintenance": maintenance,
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        pruned_count = int(retention.get("count", 0))
        reclaimed_bytes = int(maintenance.get("reclaimed_bytes", 0))
        print(
            f"백업 정리를 완료했어요. 오래된 저장본 {pruned_count}개를 정리했고, "
            f"DB 공간 {reclaimed_bytes}B를 회수했어요."
        )
    return 0


# === ANCHOR: VIB_BACKUP_CLEANUP_CMD_END ===
