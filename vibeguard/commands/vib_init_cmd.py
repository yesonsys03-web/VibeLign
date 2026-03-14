# === ANCHOR: VIB_INIT_CMD_START ===
import json
from pathlib import Path
from typing import Any, Dict, List

from vibeguard.core.meta_paths import MetaPaths
from vibeguard.core.project_scan import iter_source_files, relpath_str


CONFIG_YAML = """schema_version: 1
llm_provider: anthropic
api_key: ENV
preview_format: ascii
"""

GITIGNORE_LINE = ".vibelign/"


def _ensure_gitignore_entry(root: Path) -> None:
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        _ = gitignore_path.write_text(GITIGNORE_LINE + "\n", encoding="utf-8")
        return
    existing = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    if GITIGNORE_LINE not in existing.splitlines():
        suffix = "" if existing.endswith("\n") or not existing else "\n"
        _ = gitignore_path.write_text(
            existing + suffix + GITIGNORE_LINE + "\n", encoding="utf-8"
        )


def _build_project_map(root: Path) -> Dict[str, Any]:
    entry_files: List[str] = []
    ui_modules: List[str] = []
    core_modules: List[str] = []
    large_files: List[str] = []
    file_count = 0
    for path in iter_source_files(root):
        rel = relpath_str(root, path)
        file_count += 1
        low = rel.lower()
        if path.name in {"main.py", "app.py", "cli.py", "index.js", "main.ts"}:
            entry_files.append(rel)
        if any(
            token in low for token in ["ui", "window", "dialog", "widget", "screen"]
        ):
            ui_modules.append(rel)
        if any(
            token in low
            for token in ["core", "engine", "service", "patch", "anchor", "guard"]
        ):
            core_modules.append(rel)
        try:
            if path.stat().st_size > 12_000:
                large_files.append(rel)
        except OSError:
            continue
    return {
        "schema_version": 1,
        "project_name": root.name,
        "entry_files": sorted(entry_files),
        "ui_modules": sorted(ui_modules),
        "core_modules": sorted(core_modules),
        "large_files": sorted(large_files),
        "file_count": file_count,
    }


def run_vib_init(args: Any) -> None:
    root = Path.cwd()
    meta = MetaPaths(root)
    _ensure_gitignore_entry(root)
    meta.ensure_vibelign_dirs()
    if not meta.config_path.exists():
        _ = meta.config_path.write_text(CONFIG_YAML, encoding="utf-8")
    project_map = _build_project_map(root)
    _ = meta.project_map_path.write_text(
        json.dumps(project_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    state = {
        "schema_version": 1,
        "project_initialized": True,
        "project_map_version": 1,
        "last_scan_at": None,
        "last_anchor_run_at": None,
        "last_guard_run_at": None,
    }
    _ = meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("VibeLign 메타데이터를 초기화했습니다.")
    print(f"- {meta.config_path.relative_to(root)}")
    print(f"- {meta.project_map_path.relative_to(root)}")
    print(f"- {meta.state_path.relative_to(root)}")
    print(f"- {meta.reports_dir.relative_to(root)}/")
    print(f"- {meta.checkpoints_dir.relative_to(root)}/")
# === ANCHOR: VIB_INIT_CMD_END ===
