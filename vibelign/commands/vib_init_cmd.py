# === ANCHOR: VIB_INIT_CMD_START ===
from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from vibelign.commands.vib_start_cmd import (
    _ensure_gitignore_entry,
    _ensure_rule_files,
    _setup_project,
)
from vibelign.core.meta_paths import MetaPaths


def _ensure_core_rule_files(root: Path) -> dict[str, list[str]]:
    return _ensure_rule_files(root, overwrite=True)


def run_vib_init(args: Namespace | None) -> None:
    root = Path.cwd()
    meta = MetaPaths(root)
    force = bool(getattr(args, "force", False))
    _ = _setup_project(root, meta, force=force)

    project_map_path = meta.project_map_path
    if project_map_path.exists():
        loaded = json.loads(project_map_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            loaded["schema_version"] = 1
            _ = project_map_path.write_text(
                json.dumps(loaded, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )


# 프로젝트 초기화 로직은 vib_start_cmd.py 로 이전되었습니다.
# 이 모듈은 하위 호환성을 위해 유지됩니다.
# === ANCHOR: VIB_INIT_CMD_END ===
