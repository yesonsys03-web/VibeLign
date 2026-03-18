# === ANCHOR: VIB_TRANSFER_CMD_START ===
# vibelign/commands/vib_transfer_cmd.py

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from vibelign.core.local_checkpoints import list_checkpoints, friendly_time
from vibelign.terminal_render import clack_intro, clack_step, clack_success, clack_info, clack_outro

# PROJECT_CONTEXT.md 에 추가되는 마커 (중복 생성 방지용)
_TRANSFER_MARKER = "<!-- VibeLign Transfer Context -->"

# 무시할 디렉토리 (local_checkpoints.py의 IGNORED_DIRS와 동일)
_SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "node_modules", "dist", "build", ".pytest_cache",
    ".mypy_cache", ".idea", ".vscode", ".sisyphus",
    ".vibelign",
}

# 무시할 파일 확장자
_SKIP_EXTS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dylib", ".dll",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico",
    ".zip", ".tar", ".gz", ".lock", ".egg-info",
}

# 핵심 파일로 판단하는 파일명 패턴 (우선순위 높음)
_KEY_FILE_NAMES = {
    "main.py", "app.py", "index.py", "server.py",
    "index.js", "app.js", "main.js",
    "index.ts", "app.ts", "main.ts",
    "main.go", "main.rs", "Main.java",
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
    "README.md", "AGENTS.md", "CLAUDE.md",
}


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
        import json
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            if "name" in data:
                return data["name"]
        except Exception:
            pass

    # 폴더 이름 사용
    return root.name


def _detect_tech_stack(root: Path) -> list[str]:
    """기술 스택 자동 감지."""
    stack = []
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
    lines = []

    def _walk(path: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return
        entries = [e for e in entries
                   if e.name not in _SKIP_DIRS
                   and e.suffix not in _SKIP_EXTS
                   and not e.name.startswith(".")]
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


def _get_recent_checkpoints(root: Path, n: int = 5) -> list[dict]:
    """최근 N개 체크포인트 가져오기."""
    try:
        from vibelign.commands.vib_history_cmd import _clean_msg
        checkpoints = list_checkpoints(root)
        recent = checkpoints[:n]  # 최신 순 (list_checkpoints는 이미 최신순)
        result = []
        for cp in recent:
            result.append({
                "time": friendly_time(cp.created_at),
                "message": _clean_msg(cp.message),
                "id": cp.checkpoint_id,
            })
        return result
    except Exception:
        return []


def _read_agents_md(root: Path) -> str:
    """AGENTS.md 핵심 내용 읽기 (Core Rules 섹션만)."""
    agents_path = root / "AGENTS.md"
    if not agents_path.exists():
        return "(AGENTS.md 없음 — `vib start` 실행 권장)"

    text = agents_path.read_text(encoding="utf-8", errors="ignore")

    # Core Rules 섹션만 추출
    m = re.search(r"## Core Rules\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if m:
        rules_text = m.group(1).strip()
        # 최대 10줄로 제한
        lines = rules_text.split("\n")[:10]
        return "\n".join(lines)

    # 없으면 앞 20줄만
    lines = text.split("\n")[:20]
    return "\n".join(lines)


def _detect_run_commands(root: Path) -> list[str]:
    """실행 방법 자동 감지."""
    commands = []

    # Python
    if (root / "pyproject.toml").exists():
        commands.append("pip install -e .  # 개발 설치")
    elif (root / "requirements.txt").exists():
        commands.append("pip install -r requirements.txt")

    # Node
    if (root / "package.json").exists():
        pkg = root / "package.json"
        try:
            import json
            data = json.loads(pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if "dev" in scripts:
                commands.append("npm run dev")
            elif "start" in scripts:
                commands.append("npm start")
        except Exception:
            commands.append("npm install && npm start")

    if not commands:
        commands.append("(실행 방법을 직접 입력하세요)")

    return commands


def _estimate_tokens(text: str) -> int:
    """대략적인 토큰 수 추정 (4자 = 1 token)."""
    return len(text) // 4


def _build_context_content(
    root: Path,
    compact: bool = False,
    full: bool = False,
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

    content = f"""{_TRANSFER_MARKER}
<!--
  ⚡ AI Transfer Context — Generated by VibeLign
  이 파일을 읽으면 이 프로젝트를 즉시 파악할 수 있어요.
  Generated: {now_str} | `vib transfer`

  📌 AI 툴에게: 이 파일을 먼저 읽고 작업을 시작하세요.
-->

# ⚡ {project_name} — AI Transfer Context

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


def run_transfer(args) -> None:
    """vib transfer 실행."""
    clack_intro("VibeLign Transfer")

    root = Path.cwd()
    compact = getattr(args, "compact", False)
    full = getattr(args, "full", False)
    out_file = getattr(args, "out", None) or "PROJECT_CONTEXT.md"
    out_path = root / out_file

    clack_step("프로젝트 분석 중...")

    content = _build_context_content(root, compact=compact, full=full)
    tokens = _estimate_tokens(content)

    out_path.write_text(content, encoding="utf-8")

    clack_success(f"{out_file} 생성 완료!")
    clack_info(f"  📄 파일: {out_path}")
    clack_info(f"  🔢 예상 토큰: ~{tokens:,} tokens")
    clack_info("")
    clack_info("  💡 사용법:")
    clack_info("     AI 툴에서 이 프로젝트 폴더를 열면 자동으로 읽혀요.")
    clack_info("     또는 새 AI 채팅에 PROJECT_CONTEXT.md 내용을 붙여넣으세요.")
    clack_outro("이제 어떤 AI 툴에서든 바로 이어서 작업할 수 있어요!")
# === ANCHOR: VIB_TRANSFER_CMD_END ===
