# === ANCHOR: VIB_INIT_CMD_START ===
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from vibelign.commands.export_cmd import AGENTS_MD_CONTENT
from vibelign.core.ai_dev_system import AI_DEV_SYSTEM_CONTENT
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_scan import iter_source_files, line_count, relpath_str


CONFIG_YAML = """schema_version: 1
llm_provider: anthropic
api_key: ENV
preview_format: ascii
"""

GITIGNORE_LINE = ".vibelign/checkpoints/"
LARGE_FILE_LINE_THRESHOLD = 300


def _ensure_core_rule_files(root: Path) -> Dict[str, List[str]]:
    created: List[str] = []
    skipped: List[str] = []

    ai_dev_path = root / "AI_DEV_SYSTEM_SINGLE_FILE.md"
    if not ai_dev_path.exists():
        _ = ai_dev_path.write_text(AI_DEV_SYSTEM_CONTENT, encoding="utf-8")
        created.append("AI_DEV_SYSTEM_SINGLE_FILE.md")
    else:
        skipped.append("AI_DEV_SYSTEM_SINGLE_FILE.md")

    agents_path = root / "AGENTS.md"
    if not agents_path.exists():
        _ = agents_path.write_text(AGENTS_MD_CONTENT, encoding="utf-8")
        created.append("AGENTS.md")
    else:
        skipped.append("AGENTS.md")

    return {"created": created, "skipped": skipped}


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
    from vibelign.core.anchor_tools import collect_anchor_index

    entry_files: List[str] = []
    ui_modules: List[str] = []
    core_modules: List[str] = []
    service_modules: List[str] = []
    large_files: List[str] = []
    file_count = 0
    for path in iter_source_files(root):
        rel = relpath_str(root, path)
        file_count += 1
        low = rel.lower()
        lines = line_count(path)
        if path.name in {"main.py", "app.py", "cli.py", "index.js", "main.ts"}:
            entry_files.append(rel)
        if any(
            token in low
            for token in ["ui", "view", "views", "window", "dialog", "widget", "screen"]
        ):
            ui_modules.append(rel)
        if any(
            token in low for token in ["core", "engine", "patch", "anchor", "guard"]
        ):
            core_modules.append(rel)
        if any(
            token in low
            for token in [
                "service",
                "services",
                "api",
                "client",
                "server",
                "worker",
                "job",
                "task",
                "queue",
                "auth",
                "data",
            ]
        ):
            service_modules.append(rel)
        if lines >= LARGE_FILE_LINE_THRESHOLD:
            large_files.append(rel)
    anchor_index = collect_anchor_index(root)
    return {
        "schema_version": 2,
        "project_name": root.name,
        "entry_files": sorted(entry_files),
        "ui_modules": sorted(ui_modules),
        "core_modules": sorted(core_modules),
        "service_modules": sorted(service_modules),
        "large_files": sorted(large_files),
        "file_count": file_count,
        "anchor_index": anchor_index,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def run_vib_init(args: Any) -> Dict[str, List[str]]:
    """프로젝트 메타데이터 초기화. 생성/유지 파일 목록을 반환 (출력 없음)."""
    root = Path.cwd()
    meta = MetaPaths(root)
    _ensure_gitignore_entry(root)

    rule_files = _ensure_core_rule_files(root)
    created = list(rule_files["created"])
    skipped = list(rule_files["skipped"])

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
    created.append(str(meta.vibelign_dir.relative_to(root)) + "/")

    return {"created": created, "skipped": skipped}


def run_vib_init_cli(args: Any) -> None:
    root = Path.cwd()
    result = run_vib_init(args)
    meta = MetaPaths(root)
    project_map = json.loads(meta.project_map_path.read_text(encoding="utf-8"))

    print("VibeLign 초기 설정을 완료했습니다.")
    print(f"- project map: {meta.project_map_path.relative_to(root)}")
    print(f"- metadata dir: {meta.vibelign_dir.relative_to(root)}/")
    print(f"- entry files: {len(project_map.get('entry_files', []))}")
    print(f"- source files: {project_map.get('file_count', 0)}")

    if result["created"]:
        print("- created:")
        for item in result["created"]:
            print(f"  - {item}")
    if result["skipped"]:
        print("- kept:")
        for item in result["skipped"]:
            print(f"  - {item}")

    state = json.loads(meta.state_path.read_text(encoding="utf-8"))
    state["last_scan_at"] = datetime.now(timezone.utc).isoformat()
    _ = meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("Next steps:")
    print("- vib doctor")
    print("- vib anchor --suggest")
    print('- vib patch --preview "your request"')


# === ANCHOR: VIB_INIT_CMD_END ===
