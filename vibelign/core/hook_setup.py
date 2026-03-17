# === ANCHOR: HOOK_SETUP_START ===
import json
from pathlib import Path
from typing import Optional


from vibelign.terminal_render import cli_print
print = cli_print

# Claude Code 훅 설정 경로 (프로젝트 레벨)
_CLAUDE_SETTINGS = ".claude/settings.json"


# === ANCHOR: HOOK_SETUP_DETECT_TOOL_START ===
def detect_tool(root: Path) -> Optional[str]:
    """프로젝트 루트에서 AI 도구를 감지"""
    if (root / ".claude").is_dir():
        return "claude"
    return None
# === ANCHOR: HOOK_SETUP_DETECT_TOOL_END ===


# === ANCHOR: HOOK_SETUP_IS_HOOK_SET_START ===
def is_hook_set(root: Path, tool: str) -> bool:
    """(하위 호환) 항상 True 반환 — PostToolUse 훅은 더 이상 사용하지 않음."""
    return True
# === ANCHOR: HOOK_SETUP_IS_HOOK_SET_END ===


# === ANCHOR: HOOK_SETUP_SETUP_HOOK_IF_NEEDED_START ===
def setup_hook_if_needed(root: Path) -> None:
    """vib start 시 초기 체크포인트 1회 생성."""
    from vibelign.core.local_checkpoints import create_checkpoint
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"vibelign: checkpoint - vib start 초기 저장 ({timestamp})"
    summary = create_checkpoint(root, msg)
    if summary:
        print(f"✓ 초기 체크포인트 저장 완료! (파일 {summary.file_count}개)")
        print("  문제가 생기면 `vib undo`로 이 시점으로 되돌릴 수 있어요.")
    else:
        print("  (변경된 파일이 없어 초기 체크포인트를 건너뜁니다)")
# === ANCHOR: HOOK_SETUP_SETUP_HOOK_IF_NEEDED_END ===


# === ANCHOR: HOOK_SETUP_REMOVE_OLD_HOOK_START ===
def remove_old_hook(root: Path) -> None:
    """기존 PostToolUse 훅이 있으면 제거."""
    path = root / _CLAUDE_SETTINGS
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    hooks = data.get("hooks", {})
    post = hooks.get("PostToolUse", [])
    if not post:
        return
    # vib checkpoint 관련 항목만 제거
    new_post = [e for e in post if "vib checkpoint" not in json.dumps(e)]
    if len(new_post) == len(post):
        return  # 변경 없음
    if new_post:
        hooks["PostToolUse"] = new_post
    else:
        hooks.pop("PostToolUse", None)
    if not hooks:
        data.pop("hooks", None)
    try:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
# === ANCHOR: HOOK_SETUP_REMOVE_OLD_HOOK_END ===
# === ANCHOR: HOOK_SETUP_END ===
