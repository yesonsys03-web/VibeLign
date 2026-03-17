# === ANCHOR: HOOK_SETUP_START ===
import json
from pathlib import Path
from typing import Optional


from vibelign.terminal_render import cli_print
print = cli_print

# Claude Code 훅 설정 경로 (프로젝트 레벨)
_CLAUDE_SETTINGS = ".claude/settings.json"

# Gemini CLI 훅 설정 경로 (추후 형식 확인 후 활성화)
# _GEMINI_SETTINGS = ".gemini/settings.json"

_MARKER = "vib checkpoint"

_CLAUDE_HOOK_ENTRY = {
    "matcher": "Write|Edit|MultiEdit",
    "hooks": [{"type": "command", "command": "vib checkpoint"}],
}


# === ANCHOR: HOOK_SETUP_DETECT_TOOL_START ===
def detect_tool(root: Path) -> Optional[str]:
    """프로젝트 루트에서 AI 도구를 감지"""
    if (root / ".claude").is_dir():
        return "claude"
    # Gemini CLI: 형식 확인 후 추가 예정
    # if (root / ".gemini").is_dir():
    #     return "gemini"
    return None
# === ANCHOR: HOOK_SETUP_DETECT_TOOL_END ===


# === ANCHOR: HOOK_SETUP_IS_HOOK_SET_START ===
def is_hook_set(root: Path, tool: str) -> bool:
    """훅이 이미 설정됐는지 확인"""
    if tool == "claude":
        path = root / _CLAUDE_SETTINGS
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = data.get("hooks", {}).get("PostToolUse", [])
            return any(_MARKER in json.dumps(e) for e in entries)
        except (json.JSONDecodeError, OSError):
            return False
    return False
# === ANCHOR: HOOK_SETUP_IS_HOOK_SET_END ===


# === ANCHOR: HOOK_SETUP__SETUP_CLAUDE_HOOK_START ===
def _setup_claude_hook(root: Path) -> bool:
    """Claude Code PostToolUse 훅 추가 (기존 설정 보존)"""
    path = root / _CLAUDE_SETTINGS
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    post = hooks.setdefault("PostToolUse", [])

    if any(_MARKER in json.dumps(e) for e in post):
        return True  # 이미 있음

    post.append(_CLAUDE_HOOK_ENTRY)

    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return True
    except OSError:
        return False
# === ANCHOR: HOOK_SETUP__SETUP_CLAUDE_HOOK_END ===


# === ANCHOR: HOOK_SETUP_SETUP_HOOK_IF_NEEDED_START ===
def setup_hook_if_needed(root: Path) -> None:
    """AI 도구 감지 → 훅 미설정 시 사용자에게 제안"""
    tool = detect_tool(root)
    if tool is None:
        return

    if is_hook_set(root, tool):
        return  # 이미 설정됨, 조용히 넘어감

    tool_label = {"claude": "Claude Code"}.get(tool, tool)

    print(f"{tool_label} 를 사용 중이에요.")
    print("AI가 파일을 수정할 때마다 자동으로 checkpoint 를 저장하는 훅을 설정할 수 있어요.")

    try:
        answer = input("설정할까요? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if answer not in {"y", "yes", "ㅇ"}:
        print("나중에 설정하려면 vib start 를 다시 실행하면 돼요.")
        return

    if tool == "claude":
        ok = _setup_claude_hook(root)
    else:
        ok = False

    if ok:
        print(f"✓ {tool_label} 훅 설정 완료!")
        print("  이제 AI가 파일을 수정하면 자동으로 checkpoint 가 저장돼요.")
    else:
        print("✗ 훅 설정에 실패했어요. vib checkpoint 를 직접 실행해주세요.")
# === ANCHOR: HOOK_SETUP_SETUP_HOOK_IF_NEEDED_END ===
# === ANCHOR: HOOK_SETUP_END ===
