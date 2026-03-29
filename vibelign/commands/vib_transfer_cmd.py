# === ANCHOR: VIB_TRANSFER_CMD_START ===
# vibelign/commands/vib_transfer_cmd.py

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Protocol, TypedDict, cast

from vibelign.core.local_checkpoints import list_checkpoints, friendly_time
from vibelign.terminal_render import (
    clack_intro,
    clack_step,
    clack_success,
    clack_info,
    clack_outro,
)

# PROJECT_CONTEXT.md 에 추가되는 마커 (중복 생성 방지용)
_TRANSFER_MARKER = "<!-- VibeLign Transfer Context -->"

# 무시할 디렉토리 (local_checkpoints.py의 IGNORED_DIRS와 동일)
_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    ".sisyphus",
    ".vibelign",
}

# 무시할 파일 확장자
_SKIP_EXTS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dylib",
    ".dll",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".ico",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
    ".egg-info",
}

# 핵심 파일로 판단하는 파일명 패턴 (우선순위 높음)
_KEY_FILE_NAMES = {
    "main.py",
    "app.py",
    "index.py",
    "server.py",
    "index.js",
    "app.js",
    "main.js",
    "index.ts",
    "app.ts",
    "main.ts",
    "main.go",
    "main.rs",
    "Main.java",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
}

# handoff에서 무시할 경로 접두어
_HANDOFF_SKIP_PREFIXES = (".vibelign", ".git", "__pycache__")


class CheckpointSummary(TypedDict):
    time: str
    message: str
    id: str


class DecisionContext(TypedDict):
    tried: str
    blocked_by: str
    switched_to: str


class HandoffData(TypedDict, total=False):
    generated_at: str
    source: str
    quality: str
    session_summary: str | None
    changed_files: list[str]
    completed_work: str | None
    unfinished_work: str | None
    first_next_action: str | None
    decision_context: DecisionContext | None
    latest_checkpoint: str | None


class TransferArgs(Protocol):
    compact: bool
    full: bool
    handoff: bool
    no_prompt: bool
    print_mode: bool
    dry_run: bool
    out: str | None


_TIMESTAMP_PATTERN = re.compile(r"\s*\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)\s*$")


def _clean_checkpoint_message(msg: str) -> str:
    for prefix in ("vibelign: checkpoint - ", "vibelign: checkpoint"):
        if msg.startswith(prefix):
            msg = msg[len(prefix) :]
            break
    msg = _TIMESTAMP_PATTERN.sub("", msg).strip()
    if msg.startswith("{") or len(msg) > 200:
        return "(자동 저장)"
    return msg or "(메시지 없음)"


def _read_json_object(path: Path) -> dict[str, object] | None:
    try:
        raw_obj = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None
    if not isinstance(raw_obj, dict):
        return None
    raw = cast(dict[object, object], raw_obj)
    normalized: dict[str, object] = {}
    for key, value in raw.items():
        normalized[str(key)] = value
    return normalized


def _normalize_object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    normalized: dict[str, object] = {}
    for key, item in raw.items():
        normalized[str(key)] = item
    return normalized


def _handoff_text(value: object, default: str = "(not provided)") -> str:
    return value if isinstance(value, str) and value else default


def _handoff_files(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    raw_items = cast(list[object], value)
    items: list[str] = []
    for item in raw_items:
        if isinstance(item, str):
            items.append(item)
    return items


def _handoff_decision_context(value: object) -> DecisionContext | None:
    normalized = _normalize_object_dict(value)
    if normalized is None:
        return None
    return {
        "tried": _handoff_text(normalized.get("tried")),
        "blocked_by": _handoff_text(normalized.get("blocked_by")),
        "switched_to": _handoff_text(normalized.get("switched_to")),
    }


def _arg_bool(args: object, name: str) -> bool:
    value = getattr(args, name, False)
    return value if isinstance(value, bool) else False


def _arg_text(args: object, name: str) -> str | None:
    value = getattr(args, name, None)
    return value if isinstance(value, str) else None


def _get_changed_files(root: Path) -> list[str]:
    """git 상태에서 변경된 파일 목록 수집 (최대 10개)."""
    files: list[str] = []
    try:
        r1 = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
        )
        for f in r1.stdout.splitlines():
            f = f.strip()
            if f:
                files.append(f)

        r2 = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
        )
        for line in r2.stdout.splitlines():
            if len(line) > 3:
                fname = line[3:].strip()
                if fname not in files:
                    files.append(fname)
    except Exception:
        pass

    # 시스템 파일 제거
    files = [
        f
        for f in files
        if not any(f.startswith(p) for p in _HANDOFF_SKIP_PREFIXES)
        and not f.endswith((".pyc", ".pyo"))
    ]
    return files[:10]


def _detect_project_name(root: Path) -> str:
    """프로젝트 이름 감지."""
    # pyproject.toml에서 name 읽기
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'name\s*=\s*"([^"]+)"', text)
        if m:
            return m.group(1)

    # package.json에서 name 읽기
    pkg_json = root / "package.json"
    if pkg_json.exists():
        data = _read_json_object(pkg_json)
        name = data.get("name") if data is not None else None
        if isinstance(name, str):
            return name

    # 폴더 이름 사용
    return root.name


def _detect_tech_stack(root: Path) -> list[str]:
    """기술 스택 자동 감지."""
    stack: list[str] = []
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        stack.append("Python")
    if (root / "package.json").exists():
        pkg = root / "package.json"
        text = pkg.read_text(encoding="utf-8", errors="ignore")
        if "react" in text.lower():
            stack.append("React")
        elif "vue" in text.lower():
            stack.append("Vue")
        elif "next" in text.lower():
            stack.append("Next.js")
        else:
            stack.append("Node.js")
    if (root / "go.mod").exists():
        stack.append("Go")
    if (root / "Cargo.toml").exists():
        stack.append("Rust")
    if (root / "pom.xml").exists() or (root / "build.gradle").exists():
        stack.append("Java")
    if not stack:
        stack.append("(자동 감지 실패 — 직접 입력 권장)")
    return stack


def _build_file_tree(root: Path, max_depth: int = 3) -> str:
    """파일 트리 생성 (핵심 파일만, 최대 깊이 제한)."""
    lines: list[str] = []

    def _walk(path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return
        entries = [
            e
            for e in entries
            if e.name not in _SKIP_DIRS
            and e.suffix not in _SKIP_EXTS
            and not e.name.startswith(".")
        ]
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension, depth + 1)
            else:
                # 핵심 파일 표시
                marker = "  ⭐" if entry.name in _KEY_FILE_NAMES else ""
                lines.append(f"{prefix}{connector}{entry.name}{marker}")

    lines.append(f"{root.name}/")
    _walk(root, "", 1)
    return "\n".join(lines)


def _get_recent_checkpoints(root: Path, n: int = 5) -> list[CheckpointSummary]:
    """최근 N개 체크포인트 가져오기."""
    try:
        checkpoints = list_checkpoints(root)
        recent = checkpoints[:n]  # 최신 순 (list_checkpoints는 이미 최신순)
        result: list[CheckpointSummary] = []
        for cp in recent:
            result.append(
                {
                    "time": friendly_time(cp.created_at),
                    "message": _clean_checkpoint_message(cp.message),
                    "id": cp.checkpoint_id,
                }
            )
        return result
    except Exception:
        return []


def _read_agents_md(root: Path) -> str:
    """AGENTS.md 핵심 내용 읽기 (Core Rules + Module boundaries까지, Two Modification Modes 전)."""
    agents_path = root / "AGENTS.md"
    if not agents_path.exists():
        return "(AGENTS.md 없음 — `vib start` 실행 권장)"

    text = agents_path.read_text(encoding="utf-8", errors="ignore")

    # Core Rules부터 Two Modification Modes 직전까지 (중간의 ## Module boundaries 등 포함)
    m = re.search(
        r"## Core Rules\n(.*?)(?=\n## Two Modification Modes|\Z)",
        text,
        re.DOTALL,
    )
    if m:
        rules_text = m.group(1).strip()
        # 핸드오프 본문이 과도해지지 않도록 상한
        lines = rules_text.split("\n")[:40]
        return "\n".join(lines)

    # 없으면 앞 20줄만
    lines = text.split("\n")[:20]
    return "\n".join(lines)


def _detect_run_commands(root: Path) -> list[str]:
    """실행 방법 자동 감지."""
    commands: list[str] = []

    # Python
    if (root / "pyproject.toml").exists():
        commands.append("pip install -e .  # 개발 설치")
    elif (root / "requirements.txt").exists():
        commands.append("pip install -r requirements.txt")

    # Node
    if (root / "package.json").exists():
        pkg = root / "package.json"
        data = _read_json_object(pkg)
        scripts = data.get("scripts") if data is not None else None
        normalized_scripts = _normalize_object_dict(scripts)
        if normalized_scripts is not None:
            if "dev" in normalized_scripts:
                commands.append("npm run dev")
            elif "start" in normalized_scripts:
                commands.append("npm start")
        else:
            commands.append("npm install && npm start")

    if not commands:
        commands.append("(실행 방법을 직접 입력하세요)")

    return commands


def _estimate_tokens(text: str) -> int:
    """대략적인 토큰 수 추정 (4자 = 1 token)."""
    return len(text) // 4


def _build_handoff_block(data: HandoffData) -> str:
    """Session Handoff 블록 생성 (12줄 이하, 5 bullets 이하 목표)."""
    lines: list[str] = []
    lines.append("## Session Handoff")
    lines.append(
        "> ⚠️ This block is session-specific and time-sensitive. Read this first."
    )
    lines.append("")
    lines.append(f"Generated: {_handoff_text(data.get('generated_at'), '')}")
    lines.append(
        f"Handoff source: {_handoff_text(data.get('source'), 'file_fallback')}"
    )
    lines.append(
        f"Handoff quality: {_handoff_text(data.get('quality'), 'auto-drafted')}"
    )

    cp_ref = _handoff_text(data.get("latest_checkpoint"))
    lines.append(f"Latest checkpoint: {cp_ref}")
    lines.append("")

    lines.append("VibeLign patch rules")
    lines.append(
        "- Split composite requests into intent / source / destination / behavior_constraint"
    )
    lines.append(
        "- Treat delete + move as move + preservation unless removal is explicit"
    )
    lines.append("- Resolve source and destination by role, not with one shared rule")
    lines.append(
        "- If patch contract or codespeak shape changes, update tests and docs together"
    )
    lines.append("")

    # Bullet section (max 5)
    summary = _handoff_text(data.get("session_summary"))
    lines.append(f"- Today's work: {summary}")

    changed = _handoff_files(data.get("changed_files"))
    if changed:
        files_str = ", ".join(f"`{f}`" for f in changed[:5])
        if len(changed) > 5:
            files_str += f" … (+{len(changed) - 5})"
        lines.append(f"- Changed files: {files_str}")
    else:
        lines.append("- Changed files: (not provided)")

    completed = _handoff_text(data.get("completed_work"))
    lines.append(f"- Completed work: {completed}")

    unfinished = _handoff_text(data.get("unfinished_work"))
    lines.append(f"- Unfinished work: {unfinished}")

    next_action = _handoff_text(data.get("first_next_action"))
    lines.append(f"- Next action: {next_action}")

    # Decision context (optional)
    dc = _handoff_decision_context(data.get("decision_context"))
    if dc:
        lines.append("")
        lines.append("Decision context")
        lines.append(f"- Tried: {dc.get('tried') or '(not provided)'}")
        lines.append(f"- Blocked by: {dc.get('blocked_by') or '(not provided)'}")
        lines.append(f"- Switched to: {dc.get('switched_to') or '(not provided)'}")

    lines.append("")
    return "\n".join(lines)


def _build_context_content(
    root: Path,
    compact: bool = False,
    full: bool = False,
    handoff_data: HandoffData | None = None,
) -> str:
    """PROJECT_CONTEXT.md 내용 생성."""

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = _detect_project_name(root)
    tech_stack = _detect_tech_stack(root)
    checkpoints = _get_recent_checkpoints(root, n=3 if compact else 5)
    agents_rules = _read_agents_md(root)
    run_commands = _detect_run_commands(root)

    # 파일 트리 (compact면 깊이 2, full이면 4, 기본 3)
    max_depth = 2 if compact else (4 if full else 3)
    file_tree = _build_file_tree(root, max_depth=max_depth)

    # 마지막 작업 (최근 체크포인트 메시지)
    last_work = checkpoints[0]["message"] if checkpoints else "(체크포인트 없음)"
    last_time = checkpoints[0]["time"] if checkpoints else ""

    # 체크포인트 테이블
    cp_rows = ""
    for cp in checkpoints:
        cp_rows += f"| {cp['time']} | {cp['message']} |\n"

    # 실행 명령어
    run_cmd_str = "\n".join(f"  {cmd}" for cmd in run_commands)

    # Session Handoff 블록 (--handoff 모드일 때만)
    handoff_section = ""
    if handoff_data:
        handoff_section = _build_handoff_block(handoff_data) + "\n---\n\n"

    content = f"""{_TRANSFER_MARKER}
<!--
  ⚡ AI Transfer Context — Generated by VibeLign
  이 파일을 읽으면 이 프로젝트를 즉시 파악할 수 있어요.
  Generated: {now_str} | `vib transfer`

  📌 AI 툴에게: Session Handoff 블록을 먼저 읽고 작업을 시작하세요.
-->

{handoff_section}# ⚡ {project_name} — AI Transfer Context

> 이 파일은 `vib transfer`로 자동 생성되었습니다.
> **AI 툴이 바뀌어도 이 파일 하나로 즉시 이어서 작업 가능합니다.**

---

## 1. 지금 무엇을 작업 중인가

- **마지막 작업**: {last_time} — `{last_work}`
- **상태**: 작업 진행 중 (아래 체크포인트 기록 참고)

---

## 2. 프로젝트 요약

- **프로젝트명**: {project_name}
- **기술 스택**: {", ".join(tech_stack)}
- **루트 경로**: {root}

---

## 3. 파일 구조

```
{file_tree}
```

> ⭐ = 핵심 진입점 파일

---

## 4. 최근 체크포인트 (작업 이력)

| 시간 | 작업 내용 |
|------|-----------|
{cp_rows}
> 전체 기록: `vib history`

---

## 5. AI 작업 규칙 (AGENTS.md)

```
{agents_rules}
```

---

## 6. 실행 방법

```bash
{run_cmd_str}
```

---

## 7. VibeLign 필수 명령어

```bash
vib checkpoint "설명"  # 작업 전 반드시 저장
vib undo               # 잘못됐으면 되돌리기
vib history            # 작업 이력 보기
vib transfer           # 이 파일 갱신
```

---

*Generated by [VibeLign](https://github.com/yesonsys03-web/VibeLign) — AI 코딩 안전망*
"""
    return content


def _get_recent_commits(root: Path, n: int = 5) -> list[str]:
    """최근 사용자 커밋 메시지 가져오기 (vibelign 자동 커밋 제외)."""
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={n * 2}", "--pretty=format:%s", "--no-merges"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
        )
        messages = [m.strip() for m in result.stdout.splitlines() if m.strip()]
        # vibelign 자동 커밋 제외
        messages = [m for m in messages if not m.startswith("vibelign:")]
        return messages[:n]
    except Exception:
        return []


def _handoff_quality(data: HandoffData) -> tuple[str, str]:
    """handoff 완성도 평가. (이모지, 메시지) 반환."""
    score = 0
    missing: list[str] = []

    summary = _handoff_text(data.get("session_summary"), "")
    if summary and summary != "(not provided)":
        score += 40
    else:
        missing.append("오늘 한 작업 요약")

    next_action = _handoff_text(data.get("first_next_action"), "")
    if next_action and next_action != "(not provided)":
        score += 40
    else:
        missing.append("다음 AI가 할 일")

    if _handoff_files(data.get("changed_files")):
        score += 20

    if score >= 80:
        return "🟢", f"좋음 ({score}%)"
    elif score >= 40:
        tips = ", ".join(missing)
        return "🟡", f"보통 ({score}%) — 추가하면 좋아요: {tips}"
    else:
        tips = ", ".join(missing)
        return "🔴", f"부족 ({score}%) — 꼭 추가하세요: {tips}"


_AGENTS_HANDOFF_MARKER = "<!-- VibeLign Handoff Instruction -->"
_AGENTS_HANDOFF_BLOCK = """{marker}
## AI 전환 / Session Handoff

새 채팅을 열거나 다른 AI 툴로 이동했을 때:

1. `PROJECT_CONTEXT.md` 파일을 가장 먼저 읽으세요.
2. 파일 맨 위의 `## Session Handoff` 블록을 확인하세요.
3. `Next action` 항목에 적힌 작업부터 시작하세요.

> 이 지시는 `vib transfer --handoff` 실행 시 자동으로 추가됩니다.
""".format(marker=_AGENTS_HANDOFF_MARKER)


def _inject_agents_handoff_instruction(root: Path) -> None:
    """AGENTS.md가 있으면 handoff 읽기 지시를 추가 (중복 방지)."""
    agents_path = root / "AGENTS.md"
    if not agents_path.exists():
        return
    text = agents_path.read_text(encoding="utf-8")
    if _AGENTS_HANDOFF_MARKER in text:
        return  # 이미 있음
    _ = agents_path.write_text(
        text.rstrip() + "\n\n" + _AGENTS_HANDOFF_BLOCK, encoding="utf-8"
    )


def _collect_handoff_data_from_cli(root: Path, no_prompt: bool) -> HandoffData:
    """CLI 경로(파일 기반 폴백)로 handoff_data 수집."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    changed_files = _get_changed_files(root)
    checkpoints = _get_recent_checkpoints(root, n=1)
    latest_cp = checkpoints[0]["message"] if checkpoints else None

    data: HandoffData = {
        "generated_at": now_str,
        "source": "file_fallback",
        "quality": "auto-drafted",
        "session_summary": None,
        "changed_files": changed_files,
        "completed_work": None,
        "unfinished_work": None,
        "first_next_action": None,
        "decision_context": None,
        "latest_checkpoint": latest_cp,
    }

    # git 커밋 메시지로 session_summary 초안 생성
    recent_commits = _get_recent_commits(root, n=5)
    commit_draft = ", ".join(recent_commits) if recent_commits else None
    if commit_draft:
        data["session_summary"] = commit_draft

    if no_prompt:
        return data

    # 자동 감지 정보 출력
    clack_info("")
    clack_info("  📋 자동 감지 현황:")
    if changed_files:
        clack_info(
            f"     변경 파일: {', '.join(changed_files[:4])}"
            + (" …" if len(changed_files) > 4 else "")
        )
    else:
        clack_info("     변경 파일: (없음)")
    if latest_cp:
        clack_info(f"     최근 체크포인트: {latest_cp}")

    # git 커밋 초안 확인
    if commit_draft:
        clack_info("")
        clack_info("  💡 오늘 한 작업 초안 (최근 커밋 기반):")
        for c in recent_commits:
            clack_info(f"     • {c}")
        clack_info("")
        try:
            keep = input("  이 내용으로 할까요? (Y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            keep = ""
        if keep == "n":
            data["session_summary"] = None
            try:
                manual = input("  오늘 한 작업 요약 (한 줄): ").strip()
            except (EOFError, KeyboardInterrupt):
                manual = ""
            if manual:
                data["session_summary"] = manual
    else:
        clack_info("")
        try:
            manual = input("  오늘 한 작업 요약 (선택, 엔터 = 건너뜀): ").strip()
        except (EOFError, KeyboardInterrupt):
            manual = ""
        if manual:
            data["session_summary"] = manual

    clack_info("")

    # 필수: 다음 AI 첫 번째 할 일
    try:
        next_action = input("  다음 AI가 먼저 할 일을 한 줄로 알려주세요: ").strip()
    except (EOFError, KeyboardInterrupt):
        next_action = ""
    if next_action:
        data["first_next_action"] = next_action
        data["quality"] = "user-reviewed"

    # 선택: 방향 전환 컨텍스트
    try:
        dc_ans = input("  방향이 바뀐 게 있나요? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        dc_ans = ""
    if dc_ans == "y":
        try:
            tried = input("    Tried (시도한 것): ").strip()
            blocked = input("    Blocked by (막힌 이유): ").strip()
            switched = input("    Switched to (새 방향): ").strip()
        except (EOFError, KeyboardInterrupt):
            tried = blocked = switched = ""
        if any([tried, blocked, switched]):
            data["decision_context"] = {
                "tried": tried or "(not provided)",
                "blocked_by": blocked or "(not provided)",
                "switched_to": switched or "(not provided)",
            }

    return data


def run_transfer(args: object) -> None:
    """vib transfer 실행."""
    clack_intro("VibeLign Transfer")

    root = Path.cwd()
    compact = _arg_bool(args, "compact")
    full = _arg_bool(args, "full")
    handoff = _arg_bool(args, "handoff")
    no_prompt = _arg_bool(args, "no_prompt")
    print_mode = _arg_bool(args, "print_mode")
    dry_run = _arg_bool(args, "dry_run")
    out_file = _arg_text(args, "out") or "PROJECT_CONTEXT.md"
    out_path = root / out_file

    # --handoff와 --compact/--full 동시 사용 불가
    if handoff and (compact or full):
        clack_info("오류: --handoff는 --compact 또는 --full과 함께 사용할 수 없습니다.")
        return

    clack_step("프로젝트 분석 중...")

    if handoff:
        handoff_data = _collect_handoff_data_from_cli(root, no_prompt=no_prompt)
        content = _build_context_content(root, handoff_data=handoff_data)
    else:
        handoff_data = None
        content = _build_context_content(root, compact=compact, full=full)

    tokens = _estimate_tokens(content)

    if dry_run:
        # 파일 저장 없이 handoff 블록만 미리 출력
        clack_info("")
        clack_info("  ─── [dry-run] 저장되지 않음 ───")
        if handoff_data:
            block = _build_handoff_block(handoff_data)
            for line in block.splitlines():
                clack_info(f"  {line}")
            quality_emoji, quality_msg = _handoff_quality(handoff_data)
            clack_info("")
            clack_info(f"  handoff 품질: {quality_emoji} {quality_msg}")
        else:
            clack_info(f"  예상 토큰: ~{tokens:,} tokens")
        clack_outro("dry-run 완료 — 실제 저장하려면 --dry-run 없이 실행하세요.")
        return

    _ = out_path.write_text(content, encoding="utf-8")

    if handoff:
        _inject_agents_handoff_instruction(root)

    clack_success(f"{out_file} 생성 완료!")
    clack_info(f"  📄 파일: {out_path}")
    clack_info(f"  🔢 예상 토큰: ~{tokens:,} tokens")

    # handoff 품질 표시
    if handoff and handoff_data:
        quality_emoji, quality_msg = _handoff_quality(handoff_data)
        clack_info(f"  handoff 품질: {quality_emoji} {quality_msg}")

    if handoff and print_mode and handoff_data:
        clack_info("")
        clack_info("  ─── Session Handoff 요약 (새 AI에 붙여넣기용) ───")
        block = _build_handoff_block(handoff_data)
        for line in block.splitlines():
            clack_info(f"  {line}")

    clack_info("")
    clack_info("  💡 사용법:")
    if handoff:
        clack_info(
            "     새 AI에게 PROJECT_CONTEXT.md 상단의 Session Handoff 블록을 읽혀주세요."
        )
    else:
        clack_info("     AI 툴에서 이 프로젝트 폴더를 열면 자동으로 읽혀요.")
        clack_info("     또는 새 AI 채팅에 PROJECT_CONTEXT.md 내용을 붙여넣으세요.")
    clack_outro("이제 어떤 AI 툴에서든 바로 이어서 작업할 수 있어요!")


# === ANCHOR: VIB_TRANSFER_CMD_END ===
