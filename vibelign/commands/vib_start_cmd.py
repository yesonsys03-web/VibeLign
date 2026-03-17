import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from vibelign.commands.export_cmd import AGENTS_MD_CONTENT
from vibelign.commands.vib_doctor_cmd import build_doctor_envelope
from vibelign.core.ai_dev_system import AI_DEV_SYSTEM_CONTENT
from vibelign.core.hook_setup import detect_tool, is_hook_set, setup_hook_if_needed
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_scan import iter_source_files, line_count, relpath_str
from vibelign.terminal_render import (
    clack_info,
    clack_intro,
    clack_outro,
    clack_step,
    clack_success,
    clack_warn,
)

GITIGNORE_LINE = ".vibelign/checkpoints/"
LARGE_FILE_LINE_THRESHOLD = 300

_TREE_SKIP = {
    ".git", "__pycache__", "node_modules", ".vibelign",
    "build", "dist", ".venv", "venv", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", ".tox", "coverage",
}


def _build_tree(root: Path) -> List[str]:
    lines: List[str] = []

    def _walk(path: Path, depth: int) -> None:
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
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


def _status_line(status: str) -> str:
    if status in {"Safe", "Good"}:
        return "프로젝트 상태가 좋아요. 바로 AI 코딩을 시작해도 됩니다."
    if status == "Caution":
        return "큰 문제는 아니지만, 먼저 조금 정리하면 더 안전해요."
    return "지금은 바로 크게 수정하기보다, 먼저 문제를 확인하는 게 좋아요."


def _next_step(data: Dict[str, Any]) -> str:
    actions = data.get("recommended_actions") or []
    if actions:
        return str(actions[0])
    return "vib anchor --suggest"


def _has_git(root: Path) -> bool:
    return (root / ".git").is_dir()


def _ensure_gitignore_entry(root: Path) -> None:
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(GITIGNORE_LINE + "\n", encoding="utf-8")
        return
    existing = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    if GITIGNORE_LINE not in existing.splitlines():
        suffix = "" if existing.endswith("\n") or not existing else "\n"
        gitignore_path.write_text(
            existing + suffix + GITIGNORE_LINE + "\n", encoding="utf-8"
        )


def _ensure_rule_files(root: Path) -> Dict[str, List[str]]:
    """AI 룰 파일이 없으면 생성. 이미 있으면 건드리지 않음."""
    created: List[str] = []
    skipped: List[str] = []
    for fname, content in [
        ("AI_DEV_SYSTEM_SINGLE_FILE.md", AI_DEV_SYSTEM_CONTENT),
        ("AGENTS.md", AGENTS_MD_CONTENT),
    ]:
        path = root / fname
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(fname)
        else:
            skipped.append(fname)
    return {"created": created, "skipped": skipped}


def _classify_file(path: Path, rel: str) -> str:
    low = rel.lower()
    if path.name in {"main.py", "app.py", "cli.py", "index.js", "main.ts"}:
        return "entry"
    if any(token in low for token in ["ui", "view", "views", "window", "dialog", "widget", "screen"]):
        return "ui"
    if any(token in low for token in ["service", "services", "api", "client", "server", "worker", "job", "task", "queue", "auth", "data"]):
        return "service"
    if any(token in low for token in ["core", "engine", "patch", "anchor", "guard"]):
        return "core"
    return "other"


def _build_project_map(root: Path) -> Dict[str, Any]:
    from vibelign.core.anchor_tools import collect_anchor_index

    entry_files: List[str] = []
    ui_modules: List[str] = []
    core_modules: List[str] = []
    service_modules: List[str] = []
    large_files: List[str] = []
    file_details: Dict[str, Any] = {}
    file_count = 0
    for path in iter_source_files(root):
        rel = relpath_str(root, path)
        file_count += 1
        low = rel.lower()
        lines = line_count(path)
        category = _classify_file(path, rel)
        if category == "entry":
            entry_files.append(rel)
        if any(token in low for token in ["ui", "view", "views", "window", "dialog", "widget", "screen"]):
            ui_modules.append(rel)
        if any(token in low for token in ["core", "engine", "patch", "anchor", "guard"]):
            core_modules.append(rel)
        if any(token in low for token in ["service", "services", "api", "client", "server", "worker", "job", "task", "queue", "auth", "data"]):
            service_modules.append(rel)
        if lines >= LARGE_FILE_LINE_THRESHOLD:
            large_files.append(rel)
        file_details[rel] = {"category": category, "line_count": lines}

    anchor_index = collect_anchor_index(root)
    files = {
        rel: {
            "category": details["category"],
            "anchors": anchor_index.get(rel, []),
            "line_count": details["line_count"],
        }
        for rel, details in file_details.items()
    }
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
        "file_count": file_count,
        "anchor_index": anchor_index,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _setup_project(root: Path, meta: MetaPaths) -> Dict[str, List[str]]:
    """프로젝트 세팅: .vibelign 디렉토리, config, state, project_map, 룰 파일, .gitignore"""
    _ensure_gitignore_entry(root)
    rule_files = _ensure_rule_files(root)
    created = list(rule_files["created"])
    skipped = list(rule_files["skipped"])

    meta.ensure_vibelign_dirs()
    if not meta.config_path.exists():
        meta.config_path.write_text(CONFIG_YAML, encoding="utf-8")

    quickstart_path = meta.vibelign_dir / "VIBELIGN_QUICKSTART.md"
    if not quickstart_path.exists():
        quickstart_path.write_text(QUICKSTART_MD, encoding="utf-8")
        created.append("VIBELIGN_QUICKSTART.md")

    project_map = _build_project_map(root)
    meta.project_map_path.write_text(
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
        meta.state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        created.append(str(meta.vibelign_dir.relative_to(root)) + "/")

    return {"created": created, "skipped": skipped}


def run_vib_start(args: Any) -> None:
    root = Path.cwd()
    meta = MetaPaths(root)
    clack_intro("VibeLign 시작 설정")

    # [1] 프로젝트 세팅 (새 프로젝트면 전체, 기존이면 누락된 것만 보완)
    is_new = not meta.state_path.exists()
    if is_new:
        clack_step("처음 사용하는 프로젝트예요. 기본 설정을 준비할게요.")
    setup_result = _setup_project(root, meta)
    setup_changed: Optional[Dict[str, List[str]]] = (
        setup_result if (is_new or setup_result["created"]) else None
    )

    # [2] AI 도구 훅 설정 제안
    setup_hook_if_needed(root)

    # [3] 훅/git 상태 파악
    tool = detect_tool(root)
    hook_active = tool is not None and is_hook_set(root, tool)
    hook_label = {"claude": "Claude Code"}.get(tool, tool) if tool else None
    git_active = _has_git(root)

    # [4] 출력
    clack_step("프로젝트 상태를 확인하는 중...")
    doctor_envelope = build_doctor_envelope(root, strict=False)
    doctor_data = doctor_envelope["data"]

    if setup_changed is not None:
        clack_step("초기 설정")
        for f in setup_changed.get("created", []):
            clack_success(f"생성됨: {f}")
        for f in setup_changed.get("skipped", []):
            clack_info(f"유지됨: {f}")

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

    score = doctor_data["project_score"]
    status = doctor_data["status"]
    clack_step("프로젝트 상태")
    clack_info(f"점수: {score} / 100")
    clack_info(_status_line(status))

    if is_new:
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
        clack_info('언제든 vib doctor 로 프로젝트 상태를 확인할 수 있어요')
        clack_info('vib checkpoint "설명" 으로 현재 상태를 저장할 수 있어요 (게임 세이브)')
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
                suggest=False, auto=True, validate=False,
                dry_run=False, json=False, only_ext="",
            )
            run_vib_anchor(anchor_args)
            clack_success("앵커 삽입 완료! 이제 vib patch 로 AI에게 수정을 시킬 수 있어요")
        else:
            clack_warn(
                "아직 코드 파일이 없어서 앵커를 달 게 없어요. "
                "코드를 작성한 뒤 vib anchor 를 실행하세요!"
            )
