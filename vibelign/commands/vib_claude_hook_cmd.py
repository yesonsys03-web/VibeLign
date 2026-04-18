# === ANCHOR: VIB_CLAUDE_HOOK_CMD_START ===
from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from vibelign.core.hook_setup import (
    ensure_claude_pretooluse_hook,
    get_claude_hook_status,
    set_claude_hook_enabled,
)
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import clack_info, clack_intro, clack_success, clack_warn


# === ANCHOR: VIB_CLAUDE_HOOK_CMD_RUN_VIB_CLAUDE_HOOK_START ===
def run_vib_claude_hook(args: Namespace) -> None:
    root = resolve_project_root(Path.cwd())
    action = str(getattr(args, "action", "status"))

    if action == "enable":
        result = ensure_claude_pretooluse_hook(root)
        if result.status == "malformed-settings":
            clack_warn(
                ".claude/settings.json 형식이 올바르지 않아 자동 설치를 완료하지 못했어요."
            )
            raise SystemExit(1)
        set_claude_hook_enabled(root, True)
        clack_success("Claude PreToolUse enforcement를 켰어요.")
        if result.path is not None:
            clack_info(str(result.path))
        return

    if action == "disable":
        set_claude_hook_enabled(root, False)
        clack_success("Claude PreToolUse enforcement를 껐어요. hook 엔트리는 유지돼요.")
        return

    status = get_claude_hook_status(root)
    clack_intro("Claude hook 상태")
    clack_info(f"Claude 프로젝트 감지: {'예' if status['tool_detected'] else '아니오'}")
    clack_info(f"Hook 설치됨: {'예' if status['installed'] else '아니오'}")
    clack_info(f"Enforcement enabled: {'예' if status['enabled'] else '아니오'}")
    clack_info(str(status["settings_path"]))
# === ANCHOR: VIB_CLAUDE_HOOK_CMD_RUN_VIB_CLAUDE_HOOK_END ===
# === ANCHOR: VIB_CLAUDE_HOOK_CMD_END ===
