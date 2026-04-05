# === ANCHOR: VIB_START_CMD_START ===
import json
import shutil
import subprocess
import sys
from argparse import Namespace
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from vibelign.commands.export_cmd import (
    AGENTS_MD_CONTENT,
    export_tool_files,
    write_claude_md,
    write_cursorrules,
    write_opencode_md,
)
from vibelign.core.git_hooks import install_pre_commit_secret_hook
from vibelign.core.doctor_v2 import build_doctor_envelope
from vibelign.core.ai_dev_system import AI_DEV_SYSTEM_CONTENT
from vibelign.core.hook_setup import detect_tool, remove_old_hook, setup_hook_if_needed
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_scan import iter_source_files
from vibelign.terminal_render import (
    clack_info,
    clack_intro,
    clack_outro,
    clack_step,
    clack_success,
    clack_warn,
)

GITIGNORE_LINE = ".vibelign/checkpoints/"
GITIGNORE_SCAN_CACHE_LINE = ".vibelign/scan_cache.json"
LARGE_FILE_LINE_THRESHOLD = 300
START_TOOL_CHOICES = ("claude", "opencode", "cursor", "antigravity", "codex")
TOOL_DISPLAY_NAMES = {
    "claude": "Claude",
    "opencode": "OpenCode",
    "cursor": "Cursor",
    "antigravity": "Antigravity",
    "codex": "Codex",
}

_TREE_SKIP = {
    ".git",
    "__pycache__",
    "node_modules",
    ".vibelign",
    "build",
    "dist",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    "coverage",
}


# === ANCHOR: VIB_START_CMD__BUILD_TREE_START ===
def _build_tree(root: Path) -> list[str]:
    lines: list[str] = []

    # === ANCHOR: VIB_START_CMD__WALK_START ===
    def _walk(path: Path, depth: int) -> None:
        try:
            entries = sorted(
                path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())
            )
        except PermissionError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name in _TREE_SKIP:
                continue
            indent = "  " * depth
            if entry.is_dir():
                lines.append(f"{indent}{entry.name}/")
                _walk(entry, depth + 1)
            else:
                lines.append(f"{indent}{entry.name}")

    # === ANCHOR: VIB_START_CMD__WALK_END ===

    # === ANCHOR: VIB_START_CMD__BUILD_TREE_END ===
    _walk(root, 0)
    return lines


CONFIG_YAML = """schema_version: 1
llm_provider: anthropic
api_key: ENV
preview_format: ascii
"""

QUICKSTART_MD = """\
# VibeLign 빠른 시작 가이드

> 이 파일은 `vib start` 실행 시 자동 생성됩니다.

---

## AI에게 코드 수정 시키고 싶을 때

```
vib patch "로그인 버튼 크기 키워줘"
```
나온 결과를 복사해서 AI(ChatGPT, Claude 등)에 붙여넣기

---

## 코드에 안전 표식(앵커) 달기

```
vib anchor --auto
```
AI가 정확한 위치를 찾을 수 있도록 코드에 표식을 달아요.
처음 한 번만 실행하면 돼요.

---

## AI가 수정한 결과 확인하기

```
vib guard
```
AI가 이상한 곳을 건드리지 않았는지 자동으로 검사해요.

---

## 현재 상태 저장하기 (게임 세이브)

```
vib checkpoint "로그인 완성"
```
나중에 되돌리고 싶으면: `vib undo`

---

## 프로젝트 상태 확인하기

```
vib doctor
```
프로젝트 건강 점수와 해결 방법을 알려줘요.
"""


# === ANCHOR: VIB_START_CMD__STATUS_LINE_START ===
def _status_line(status: str) -> str:
    if status in {"Safe", "Good"}:
        return "프로젝트 상태가 좋아요. 바로 AI 코딩을 시작해도 됩니다."
    if status == "Caution":
        return "큰 문제는 아니지만, 먼저 조금 정리하면 더 안전해요."
    return "지금은 바로 크게 수정하기보다, 먼저 문제를 확인하는 게 좋아요."


# === ANCHOR: VIB_START_CMD__STATUS_LINE_END ===


# === ANCHOR: VIB_START_CMD__NEXT_STEP_START ===
def _next_step(data: dict[str, object]) -> str:
    raw_actions = data.get("recommended_actions")
    actions = cast(list[object], raw_actions) if isinstance(raw_actions, list) else []
    if actions:
        return str(actions[0])
    return "vib anchor --suggest"


# === ANCHOR: VIB_START_CMD__NEXT_STEP_END ===


# === ANCHOR: VIB_START_CMD__HAS_GIT_START ===
def _has_git(root: Path) -> bool:
    return (root / ".git").is_dir()


def _find_git_exe() -> str | None:
    found = shutil.which("git")
    if found:
        return found
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Git\mingw64\bin\git.exe",
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\mingw64\bin\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (Arm)\Git\mingw64\bin\git.exe",
            r"C:\Program Files (Arm)\Git\cmd\git.exe",
        ]
        for p in candidates:
            if Path(p).exists():
                return p
    return None


def _init_git(root: Path) -> bool:
    """git init 실행. 성공하면 True, 실패하면 False."""
    git = _find_git_exe()
    if not git:
        return False
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        subprocess.run(
            [git, "init"],
            cwd=root,
            check=True,
            capture_output=True,
            creationflags=flags,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


# === ANCHOR: VIB_START_CMD__HAS_GIT_END ===


# === ANCHOR: VIB_START_CMD__ENSURE_GITIGNORE_ENTRY_START ===
def _ensure_gitignore_entry(root: Path) -> None:
    gitignore_path = root / ".gitignore"
    lines_to_add = [
        line
        for line in [GITIGNORE_LINE, GITIGNORE_SCAN_CACHE_LINE]
        if line
        not in (
            gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if gitignore_path.exists()
            else []
        )
    ]
    if not lines_to_add:
        return
    if not gitignore_path.exists():
        _ = gitignore_path.write_text("\n".join(lines_to_add) + "\n", encoding="utf-8")
        return
    existing = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    suffix = "" if existing.endswith("\n") or not existing else "\n"
    _ = gitignore_path.write_text(
        existing + suffix + "\n".join(lines_to_add) + "\n", encoding="utf-8"
    )


# === ANCHOR: VIB_START_CMD__ENSURE_GITIGNORE_ENTRY_END ===


# === ANCHOR: VIB_START_CMD__ENSURE_RULE_FILES_START ===
def _ensure_rule_files(root: Path, overwrite: bool = True) -> dict[str, list[str]]:
    created: list[str] = []
    updated: list[str] = []
    for fname, content in [
        ("AI_DEV_SYSTEM_SINGLE_FILE.md", AI_DEV_SYSTEM_CONTENT),
        ("AGENTS.md", AGENTS_MD_CONTENT),
    ]:
        path = root / fname
        if not path.exists():
            _ = path.write_text(content, encoding="utf-8")
            created.append(fname)
        elif overwrite:
            backup = root / (fname + "~")
            _ = backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            _ = path.write_text(content, encoding="utf-8")
            updated.append(fname)
        else:
            continue
    return {"created": created, "updated": updated}


# === ANCHOR: VIB_START_CMD__ENSURE_RULE_FILES_END ===


# === ANCHOR: VIB_START_CMD__BUILD_PROJECT_MAP_START ===
def _build_project_map(root: Path, force_scan: bool = False) -> dict[str, object]:
    from vibelign.core.meta_paths import MetaPaths
    from vibelign.core.scan_cache import incremental_scan

    ui_tokens = ["ui", "view", "views", "window", "dialog", "widget", "screen"]
    service_tokens = [
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
    core_tokens = ["core", "engine", "patch", "anchor", "guard"]

    meta = MetaPaths(root)
    meta.ensure_vibelign_dir()
    scan = incremental_scan(root, meta.scan_cache_path, force=force_scan)

    entry_files: list[str] = []
    ui_modules: list[str] = []
    core_modules: list[str] = []
    service_modules: list[str] = []
    large_files: list[str] = []
    anchor_index: dict[str, object] = {}
    files: dict[str, object] = {}

    for rel, data in scan.items():
        low = rel.lower()
        category = str(data["category"])
        anchors = data["anchors"]
        raw_lines = data["line_count"]
        lines = raw_lines if isinstance(raw_lines, int) else 0

        if category == "entry":
            entry_files.append(rel)
        if any(t in low for t in ui_tokens):
            ui_modules.append(rel)
        if any(t in low for t in core_tokens):
            core_modules.append(rel)
        if any(t in low for t in service_tokens):
            service_modules.append(rel)
        if lines >= LARGE_FILE_LINE_THRESHOLD:
            large_files.append(rel)
        if anchors:
            anchor_index[rel] = anchors
        files[rel] = {"category": category, "anchors": anchors, "line_count": lines}

    return {
        "schema_version": 2,
        "project_name": root.name,
        "tree": _build_tree(root),
        "files": files,
        "entry_files": sorted(entry_files),
        "ui_modules": sorted(ui_modules),
        "core_modules": sorted(core_modules),
        "service_modules": sorted(service_modules),
        "large_files": sorted(large_files),
        "file_count": len(scan),
        "anchor_index": anchor_index,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


# === ANCHOR: VIB_START_CMD__BUILD_PROJECT_MAP_END ===


# === ANCHOR: VIB_START_CMD__REGISTER_MCP_START ===
def _register_mcp_claude(root: Path) -> bool:
    """Claude Code .claude/settings.json에 vibelign MCP 서버를 등록한다.
    이미 등록되어 있으면 False, 새로 등록하면 True 반환."""
    claude_dir = root / ".claude"
    settings_path = claude_dir / "settings.json"
    claude_dir.mkdir(exist_ok=True)

    if settings_path.exists():
        try:
            loaded = cast(object, json.loads(settings_path.read_text(encoding="utf-8")))
            settings = (
                cast(dict[str, object], loaded) if isinstance(loaded, dict) else {}
            )
        except (json.JSONDecodeError, OSError):
            # 손상된 파일을 백업하고 새로 시작
            backup = settings_path.with_suffix(".json.bak")
            _ = settings_path.rename(backup)
            clack_warn(
                f".claude/settings.json 파일이 손상되어 백업했습니다. ({backup.name})\n  MCP 등록을 새로 진행합니다."
            )
            settings = {}
    else:
        settings = {}

    existing_mcp_servers = settings.get("mcpServers")
    mcp_servers = (
        cast(dict[str, object], existing_mcp_servers)
        if isinstance(existing_mcp_servers, dict)
        else {}
    )
    settings["mcpServers"] = mcp_servers
    if "vibelign" in mcp_servers:
        return False

    mcp_servers["vibelign"] = {"command": "vibelign-mcp", "args": []}
    _ = settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def _register_mcp_cursor(root: Path) -> bool:
    cursor_dir = root / ".cursor"
    settings_path = cursor_dir / "mcp.json"
    cursor_dir.mkdir(exist_ok=True)

    if settings_path.exists():
        try:
            loaded = cast(object, json.loads(settings_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            backup = settings_path.with_suffix(".json.bak")
            _ = settings_path.rename(backup)
            clack_warn(
                f".cursor/mcp.json 파일이 손상되어 백업했습니다. ({backup.name})\n  MCP 등록을 새로 진행합니다."
            )
            settings: dict[str, object] = {}
        else:
            if isinstance(loaded, dict):
                settings = cast(dict[str, object], loaded)
            else:
                backup = settings_path.with_suffix(".json.bak")
                _ = settings_path.rename(backup)
                clack_warn(
                    f".cursor/mcp.json 형식이 올바르지 않아 백업했습니다. ({backup.name})\n  MCP 등록을 새로 진행합니다."
                )
                settings = {}
    else:
        settings = {}

    mcp_servers = settings.get("mcpServers")
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}
        settings["mcpServers"] = mcp_servers

    if "vibelign" in mcp_servers:
        return False

    mcp_servers["vibelign"] = {"command": "vibelign-mcp", "args": []}
    _ = settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


# === ANCHOR: VIB_START_CMD__REGISTER_MCP_END ===


def _parse_start_tools(raw: str | None) -> list[str]:
    if not raw:
        return []

    selected: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        tool = item.strip().lower()
        if not tool:
            continue
        if tool not in START_TOOL_CHOICES:
            options = ", ".join(START_TOOL_CHOICES)
            raise ValueError(f"지원하지 않는 도구예요: {tool} (선택지: {options})")
        if tool not in seen:
            selected.append(tool)
            seen.add(tool)
    return selected


def _selected_start_tools(args: Namespace) -> list[str]:
    if getattr(args, "all_tools", False):
        return list(START_TOOL_CHOICES)
    return _parse_start_tools(getattr(args, "tools", None))


def _configure_start_tools(
    root: Path, tools: list[str], force: bool = False
) -> list[str]:
    created: list[str] = []

    for tool in tools:
        if tool == "claude":
            _ = export_tool_files(root, "claude", overwrite=force)
            result = write_claude_md(root)
            if result == "created":
                created.append("CLAUDE.md")
            elif result == "appended":
                created.append("CLAUDE.md (규칙 추가)")
            if _register_mcp_claude(root):
                created.append(".claude/settings.json (MCP 등록)")
            continue

        if tool == "opencode":
            _ = export_tool_files(root, "opencode", overwrite=force)
            result = write_opencode_md(root)
            if result == "created":
                created.append("OPENCODE.md")
            elif result == "appended":
                created.append("OPENCODE.md (규칙 추가)")
            continue

        if tool == "cursor":
            _ = export_tool_files(root, "cursor", overwrite=force)
            result = write_cursorrules(root)
            if result == "created":
                created.append(".cursorrules")
            elif result == "appended":
                created.append(".cursorrules (규칙 추가)")
            if _register_mcp_cursor(root):
                created.append(".cursor/mcp.json (MCP 등록)")
            continue

        if tool == "antigravity":
            _ = export_tool_files(root, "antigravity", overwrite=force)
            created.append("vibelign_exports/antigravity/")
            continue

        if tool == "codex":
            _ = export_tool_files(root, "codex", overwrite=force)
            created.append("vibelign_exports/codex/")

    return created


def _tool_readiness(tools: list[str]) -> dict[str, list[str]]:
    ready: list[str] = []
    almost_ready: list[str] = []

    for tool in tools:
        label = TOOL_DISPLAY_NAMES[tool]
        if tool in {"claude", "antigravity", "opencode", "cursor"}:
            ready.append(label)
        else:
            almost_ready.append(label)

    return {"ready": ready, "almost_ready": almost_ready}


def _print_tool_readiness_summary(tools: list[str]) -> None:
    if not tools:
        return

    readiness = _tool_readiness(tools)
    ready = readiness["ready"]
    almost_ready = readiness["almost_ready"]

    clack_step("AI 도구 준비 상태")
    if ready:
        clack_info("지금 바로 사용할 수 있어요")
        for tool in ready:
            clack_info(f"- {tool}")
    if almost_ready:
        clack_info("거의 끝났어요")
        for tool in almost_ready:
            clack_info(f"- {tool}")
        if "Codex" in almost_ready:
            clack_info("  Codex: Codex 설정에 VibeLign을 한 번만 연결하세요.")


# === ANCHOR: VIB_START_CMD__SETUP_PROJECT_START ===
def _setup_project(
    root: Path, meta: MetaPaths, force: bool = False
) -> dict[str, list[str]]:
    """프로젝트 세팅: .vibelign 디렉토리, config, state, project_map, 룰 파일, .gitignore"""
    _ensure_gitignore_entry(root)
    rule_files = _ensure_rule_files(root, overwrite=force)
    created = list(rule_files["created"])
    updated = list(rule_files["updated"])

    meta.ensure_vibelign_dirs()
    if not meta.config_path.exists():
        _ = meta.config_path.write_text(CONFIG_YAML, encoding="utf-8")

    quickstart_path = meta.vibelign_dir / "VIBELIGN_QUICKSTART.md"
    if not quickstart_path.exists():
        _ = quickstart_path.write_text(QUICKSTART_MD, encoding="utf-8")
        created.append("VIBELIGN_QUICKSTART.md")

    project_map = _build_project_map(root)
    _ = meta.project_map_path.write_text(
        json.dumps(project_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if not meta.state_path.exists():
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

    return {"created": created, "updated": updated}


# === ANCHOR: VIB_START_CMD__SETUP_PROJECT_END ===


# === ANCHOR: VIB_START_CMD_RUN_VIB_START_START ===
def run_vib_start(args: Namespace) -> None:
    root = Path.cwd()
    meta = MetaPaths(root)
    clack_intro("VibeLign 시작 설정")
    try:
        selected_tools = _selected_start_tools(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    # [1] 프로젝트 세팅 (새 프로젝트면 전체, 기존이면 누락된 것만 보완)
    is_new = not meta.state_path.exists()
    if is_new:
        clack_step("처음 사용하는 프로젝트예요. 기본 설정을 준비할게요.")
    force = getattr(args, "force", False)
    setup_result = _setup_project(root, meta, force=force)
    tool_created = _configure_start_tools(root, selected_tools, force=force)
    if tool_created:
        setup_result["created"].extend(tool_created)
    setup_changed: dict[str, list[str]] | None = (
        setup_result
        if (is_new or setup_result["created"] or setup_result["updated"])
        else None
    )

    # [2] 기존 PostToolUse 훅 정리 + 초기 체크포인트 생성
    remove_old_hook(root)
    setup_hook_if_needed(root)

    # [3] AI 도구 감지
    tool = detect_tool(root)
    hook_active = False  # PostToolUse 훅은 더 이상 사용하지 않음
    hook_label = {"claude": "Claude Code"}.get(tool, tool) if tool else None
    git_active = _has_git(root)
    if not git_active:
        if _init_git(root):
            git_active = True
            clack_success("git 저장소를 자동으로 초기화했어요 (git init)")
        else:
            clack_warn("git을 찾을 수 없어서 자동 초기화를 건너뜠어요. git을 설치하면 비밀정보 자동 검사 등을 쓸 수 있어요.")
    secret_hook_result = install_pre_commit_secret_hook(root) if git_active else None

    # [4] 출력
    clack_step("프로젝트 상태를 확인하는 중...")
    doctor_envelope = build_doctor_envelope(root, strict=False)
    doctor_data = doctor_envelope["data"]

    if setup_changed is not None:
        clack_step("초기 설정")
        for f in setup_changed.get("created", []):
            clack_success(f"생성됨: {f}")
        for f in setup_changed.get("updated", []):
            clack_success(f"업데이트됨: {f}  (기존 파일 → {f}~)")

    _print_tool_readiness_summary(selected_tools)

    if hook_label and hook_active:
        clack_step("AI 도구 연동")
        clack_success(f"{hook_label} 훅이 활성화돼요")
        clack_info("AI가 파일을 수정하면 자동으로 checkpoint가 저장돼요")
    elif not hook_active and not git_active:
        clack_step("변경사항 추적 안내")
        clack_info(
            "AI 작업 후 `vib checkpoint`를 실행하면 변경 내역을 안전하게 남길 수 있어요"
        )
        clack_info("git을 사용하면 별도 명령어 없이 자동 추적돼요")

    if secret_hook_result is not None:
        clack_step("비밀정보 커밋 보호")
        if secret_hook_result.status in {"installed", "updated"}:
            clack_success("Git 커밋 전에 API 키/토큰/개인키를 자동 검사해요")
        elif secret_hook_result.status == "chmod-failed":
            clack_warn(
                "비밀정보 자동 검사 파일은 만들었지만 실행 준비를 끝내지 못했어요"
            )
            if secret_hook_result.detail:
                clack_info(secret_hook_result.detail)
        elif secret_hook_result.status == "existing-hook":
            clack_warn(
                "이미 다른 커밋 자동 실행 설정이 있어서 비밀정보 자동 검사를 따로 켜지 않았어요"
            )
            clack_info("그 설정 안에 `vib secrets --staged`를 넣으면 같이 쓸 수 있어요")

    # [5] 고속 도구 자동 설치 제안 (watchdog은 vib watch 실행 시에만 설치 제안)
    from vibelign.core.fast_tools import has_fd, has_rg
    from vibelign.core import auto_install as auto_install_mod

    try_install_fast_tools = cast(
        Callable[[list[str], object, object, object], None],
        auto_install_mod.try_install_fast_tools,
    )
    ensure_pyproject_toml = cast(
        Callable[[Path, object, object, object], bool],
        auto_install_mod.ensure_pyproject_toml,
    )

    missing_tools: list[str] = []
    if not has_fd():
        missing_tools.append("fd")
    if not has_rg():
        missing_tools.append("ripgrep")
    if missing_tools:
        try_install_fast_tools(missing_tools, clack_info, clack_warn, clack_success)

    # [6] pyproject.toml 없으면 생성 제안
    _ = ensure_pyproject_toml(root, clack_info, clack_warn, clack_success)

    doctor_data = cast(dict[str, object], doctor_data)
    score = doctor_data["project_score"]
    status = str(doctor_data["status"])
    clack_step("프로젝트 상태")
    clack_info(f"점수: {score} / 100")
    clack_info(_status_line(status))

    if is_new:
        clack_step("딱 3가지만 기억하세요")
        clack_info("")
        clack_info('  1. 작업 전엔 항상   →  vib checkpoint "설명"')
        clack_info("  2. AI가 망쳤으면    →  vib undo")
        clack_info('  3. 잘 됐으면        →  vib checkpoint "완료"')
        clack_info("")
        clack_step("이제 이렇게 진행하면 돼요")
        clack_info("")
        clack_info("1단계: 안전 구역 만들기 (1번만 하면 돼요)")
        clack_info("   vib anchor --auto")
        clack_info("   코드에 표식을 달아서 AI가 정확한 위치를 찾게 해요")
        clack_info("")
        clack_info("2단계: AI에게 코드 수정 시키기")
        clack_info('   vib patch "원하는 변경사항"')
        clack_info("   AI가 이해하기 쉬운 형태로 바꿔줘요. 복사해서 AI에 붙여넣으세요")
        clack_info("")
        clack_info("3단계: 수정 결과 확인하기")
        clack_info("   vib guard")
        clack_info("   AI가 이상한 곳을 건드리지 않았는지 자동으로 검사해요")
        clack_info("")
        clack_info("언제든 vib doctor 로 프로젝트 상태를 확인할 수 있어요")
        clack_info("")
        clack_info("💡 탭키로 명령어 자동완성을 쓰고 싶다면:")
        clack_info("   vib completion --install")
        clack_info("")
        clack_step("지금 첫 번째 체크포인트를 저장할까요?")
        clack_info("  나중에 AI가 뭔가 망쳐도 지금 이 시점으로 되돌릴 수 있어요")
        try:
            answer = input("  [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt, OSError):
            answer = "n"
        if answer in ("", "y", "yes"):
            import types
            from vibelign.commands.vib_checkpoint_cmd import run_vib_checkpoint

            cp_args = types.SimpleNamespace(message=["시작"])
            run_vib_checkpoint(cp_args)
            clack_success("체크포인트 저장 완료! 이제 안심하고 AI 코딩을 시작하세요 🎉")
        else:
            clack_info('나중에 직접 저장하려면: vib checkpoint "시작"')
        clack_outro("준비 완료! 위 단계를 따라해 보세요")
    else:
        next_step = _next_step(doctor_data)
        clack_outro(f"다음 할 일: {next_step}")

    # --quickstart: start 직후 anchor --auto 자동 실행
    if getattr(args, "quickstart", False):
        import types
        from vibelign.commands.vib_anchor_cmd import run_vib_anchor

        has_files = any(True for _ in iter_source_files(root))
        if has_files:
            clack_step("빠른 시작: 앵커 자동 삽입 중...")
            anchor_args = types.SimpleNamespace(
                suggest=False,
                auto=True,
                validate=False,
                dry_run=False,
                json=False,
                only_ext="",
            )
            run_vib_anchor(anchor_args)
            clack_success(
                "앵커 삽입 완료! 이제 vib patch 로 AI에게 수정을 시킬 수 있어요"
            )
        else:
            clack_warn(
                "아직 코드 파일이 없어서 앵커를 달 게 없어요. 코드를 작성한 뒤 vib anchor 를 실행하세요!"
            )


# === ANCHOR: VIB_START_CMD_RUN_VIB_START_END ===
# === ANCHOR: VIB_START_CMD_END ===
