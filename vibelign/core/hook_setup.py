# === ANCHOR: HOOK_SETUP_START ===
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import cli_print

print = cli_print

_CLAUDE_SETTINGS = ".claude/settings.json"
_PRETOOLUSE_MARKER = "vibelign-claude-pretooluse-v1"


@dataclass(frozen=True)
# === ANCHOR: HOOK_SETUP_CLAUDEHOOKRESULT_START ===
class ClaudeHookResult:
    status: str
    path: Path | None
    detail: str | None = None
# === ANCHOR: HOOK_SETUP_CLAUDEHOOKRESULT_END ===


# === ANCHOR: HOOK_SETUP_DETECT_TOOL_START ===
def detect_tool(root: Path) -> str | None:
    """프로젝트 루트에서 AI 도구를 감지"""
    if (root / ".claude").is_dir():
        return "claude"
    return None
# === ANCHOR: HOOK_SETUP_DETECT_TOOL_END ===


# === ANCHOR: HOOK_SETUP__CLAUDE_SETTINGS_PATH_START ===
def _claude_settings_path(root: Path) -> Path:
    return root / _CLAUDE_SETTINGS
# === ANCHOR: HOOK_SETUP__CLAUDE_SETTINGS_PATH_END ===


# === ANCHOR: HOOK_SETUP__LOAD_SETTINGS_START ===
def _load_settings(path: Path) -> tuple[dict[str, object] | None, str | None]:
    if not path.exists():
        return {}, None
    try:
        loaded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return None, "malformed-settings"
    if not isinstance(loaded, dict):
        return None, "malformed-settings"
    return cast(dict[str, object], loaded), None
# === ANCHOR: HOOK_SETUP__LOAD_SETTINGS_END ===


# === ANCHOR: HOOK_SETUP__PRECHECK_COMMAND_START ===
def _precheck_command() -> str:
    vib_path = shutil.which("vib")
    if vib_path:
        return f'"{vib_path}" pre-check'
    return f'"{sys.executable}" -m vibelign.cli.vib_cli pre-check'
# === ANCHOR: HOOK_SETUP__PRECHECK_COMMAND_END ===


# === ANCHOR: HOOK_SETUP__MANAGED_PRETOOLUSE_ENTRY_START ===
def _managed_pretooluse_entry() -> dict[str, object]:
    return {
        "matcher": "Write",
        "hooks": [
            {
                "type": "command",
                "command": _precheck_command(),
                "marker": _PRETOOLUSE_MARKER,
            }
        ],
    }
# === ANCHOR: HOOK_SETUP__MANAGED_PRETOOLUSE_ENTRY_END ===


# === ANCHOR: HOOK_SETUP__IS_MANAGED_ENTRY_START ===
def _is_managed_entry(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    item_dict = cast(dict[str, object], item)
    hooks = item_dict.get("hooks")
    if not isinstance(hooks, list):
        return False
    for hook in cast(list[object], hooks):
        if isinstance(hook, dict):
            hook_dict = cast(dict[str, object], hook)
            if hook_dict.get("marker") == _PRETOOLUSE_MARKER:
                return True
    return False
# === ANCHOR: HOOK_SETUP__IS_MANAGED_ENTRY_END ===


# === ANCHOR: HOOK_SETUP_IS_HOOK_SET_START ===
def is_hook_set(root: Path, tool: str) -> bool:
    if tool != "claude":
        return False
    settings, error = _load_settings(_claude_settings_path(root))
    if error or settings is None:
        return False
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    hooks_dict = cast(dict[str, object], hooks)
    pretooluse = hooks_dict.get("PreToolUse", [])
    if not isinstance(pretooluse, list):
        return False
    return any(_is_managed_entry(item) for item in cast(list[object], pretooluse))
# === ANCHOR: HOOK_SETUP_IS_HOOK_SET_END ===


# === ANCHOR: HOOK_SETUP__READ_CONFIG_TEXT_START ===
def _read_config_text(meta: MetaPaths) -> str:
    if not meta.config_path.exists():
        return ""
    try:
        return meta.config_path.read_text(encoding="utf-8")
    except OSError:
        return ""
# === ANCHOR: HOOK_SETUP__READ_CONFIG_TEXT_END ===


# === ANCHOR: HOOK_SETUP_IS_CLAUDE_HOOK_ENABLED_START ===
def is_claude_hook_enabled(root: Path) -> bool:
    meta = MetaPaths(root)
    content = _read_config_text(meta)
    for line in content.splitlines():
        if line.strip().startswith("claude_hook_enabled:"):
            value = line.split(":", 1)[1].strip().lower()
            return value != "false"
    return True
# === ANCHOR: HOOK_SETUP_IS_CLAUDE_HOOK_ENABLED_END ===


# === ANCHOR: HOOK_SETUP_SET_CLAUDE_HOOK_ENABLED_START ===
def set_claude_hook_enabled(root: Path, enabled: bool) -> None:
    meta = MetaPaths(root)
    meta.ensure_vibelign_dir()
    content = _read_config_text(meta)
    lines = content.splitlines() if content else ["schema_version: 1"]
    updated = False
    for index, line in enumerate(lines):
        if line.strip().startswith("claude_hook_enabled:"):
            lines[index] = f"claude_hook_enabled: {'true' if enabled else 'false'}"
            updated = True
            break
    if not updated:
        lines.append(f"claude_hook_enabled: {'true' if enabled else 'false'}")
    _ = meta.config_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
# === ANCHOR: HOOK_SETUP_SET_CLAUDE_HOOK_ENABLED_END ===


# === ANCHOR: HOOK_SETUP_GET_CLAUDE_HOOK_STATUS_START ===
def get_claude_hook_status(root: Path) -> dict[str, object]:
    return {
        "tool_detected": detect_tool(root) == "claude",
        "installed": is_hook_set(root, "claude"),
        "enabled": is_claude_hook_enabled(root),
        "settings_path": str(_claude_settings_path(root)),
    }
# === ANCHOR: HOOK_SETUP_GET_CLAUDE_HOOK_STATUS_END ===


# === ANCHOR: HOOK_SETUP_IS_AI_ENHANCEMENT_ENABLED_START ===
def is_ai_enhancement_enabled(root: Path) -> bool:
    """`.vibelign/config.yaml` 의 `ai_enhancement` 플래그를 읽는다. 기본 False (옵트인)."""
    meta = MetaPaths(root)
    content = _read_config_text(meta)
    for line in content.splitlines():
        if line.strip().startswith("ai_enhancement:"):
            value = line.split(":", 1)[1].strip().lower()
            return value == "true"
    return False
# === ANCHOR: HOOK_SETUP_IS_AI_ENHANCEMENT_ENABLED_END ===


# === ANCHOR: HOOK_SETUP_SET_AI_ENHANCEMENT_ENABLED_START ===
def set_ai_enhancement_enabled(root: Path, enabled: bool) -> None:
    meta = MetaPaths(root)
    meta.ensure_vibelign_dir()
    content = _read_config_text(meta)
    lines = content.splitlines() if content else ["schema_version: 1"]
    updated = False
    for index, line in enumerate(lines):
        if line.strip().startswith("ai_enhancement:"):
            lines[index] = f"ai_enhancement: {'true' if enabled else 'false'}"
            updated = True
            break
    if not updated:
        lines.append(f"ai_enhancement: {'true' if enabled else 'false'}")
    _ = meta.config_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
# === ANCHOR: HOOK_SETUP_SET_AI_ENHANCEMENT_ENABLED_END ===


# === ANCHOR: HOOK_SETUP_ENSURE_CLAUDE_PRETOOLUSE_HOOK_START ===
def ensure_claude_pretooluse_hook(root: Path) -> ClaudeHookResult:
    settings_path = _claude_settings_path(root)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings, error = _load_settings(settings_path)
    if error or settings is None:
        return ClaudeHookResult(status="malformed-settings", path=settings_path)

    hooks_obj = settings.get("hooks")
    if hooks_obj is not None and not isinstance(hooks_obj, dict):
        return ClaudeHookResult(status="malformed-settings", path=settings_path)
    hooks = cast(dict[str, object], hooks_obj) if isinstance(hooks_obj, dict) else {}
    settings["hooks"] = hooks
    pretooluse_obj = hooks.get("PreToolUse")
    if pretooluse_obj is not None and not isinstance(pretooluse_obj, list):
        return ClaudeHookResult(status="malformed-settings", path=settings_path)
    pretooluse = (
        cast(list[object], pretooluse_obj) if isinstance(pretooluse_obj, list) else []
    )

    managed_entry = _managed_pretooluse_entry()
    new_items: list[object] = []
    replaced = False
    found = False
    for item in pretooluse:
        if _is_managed_entry(item):
            if not found:
                found = True
                if item != managed_entry:
                    new_items.append(managed_entry)
                    replaced = True
                else:
                    new_items.append(item)
            else:
                replaced = True
            continue
        new_items.append(item)
    if not found:
        new_items.append(managed_entry)

    hooks["PreToolUse"] = new_items
    _ = settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if not found:
        return ClaudeHookResult(status="installed", path=settings_path)
    if replaced:
        return ClaudeHookResult(status="updated", path=settings_path)
    return ClaudeHookResult(status="already-set", path=settings_path)
# === ANCHOR: HOOK_SETUP_ENSURE_CLAUDE_PRETOOLUSE_HOOK_END ===


# === ANCHOR: HOOK_SETUP_SETUP_HOOK_IF_NEEDED_START ===
def setup_hook_if_needed(root: Path) -> ClaudeHookResult | None:
    from datetime import datetime

    from vibelign.core.local_checkpoints import create_checkpoint, list_checkpoints

    existing = list_checkpoints(root)
    if not (existing and "vib start 초기 저장" in existing[0].message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"vibelign: checkpoint - vib start 초기 저장 ({timestamp})"
        summary = create_checkpoint(root, msg)
        if summary:
            print(f"✓ 초기 체크포인트 저장 완료! (파일 {summary.file_count}개)")
            print("  문제가 생기면 `vib undo`로 이 시점으로 되돌릴 수 있어요.")
        else:
            print("  (변경된 파일이 없어 초기 체크포인트를 건너뜁니다)")

    if detect_tool(root) != "claude":
        return None
    result = ensure_claude_pretooluse_hook(root)
    if result.status == "malformed-settings":
        print(
            "⚠ .claude/settings.json 형식이 올바르지 않아 Claude hook 자동 설치를 건너뜁니다."
        )
        print(
            "  settings.json을 수동으로 복구한 뒤 `vib claude-hook enable`을 실행하세요."
        )
    return result
# === ANCHOR: HOOK_SETUP_SETUP_HOOK_IF_NEEDED_END ===


# === ANCHOR: HOOK_SETUP_REMOVE_OLD_HOOK_START ===
def remove_old_hook(root: Path) -> None:
    path = _claude_settings_path(root)
    if not path.exists():
        return
    settings, error = _load_settings(path)
    if error or settings is None:
        return
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return
    hooks_dict = cast(dict[str, object], hooks)
    post = hooks_dict.get("PostToolUse", [])
    if not isinstance(post, list):
        return
    if not post:
        return
    post_items = cast(list[object], post)
    new_post: list[object] = [
        item for item in post_items if "vib checkpoint" not in json.dumps(item)
    ]
    if len(new_post) == len(post_items):
        return
    if new_post:
        hooks_dict["PostToolUse"] = new_post
    else:
        _ = hooks_dict.pop("PostToolUse", None)
    if not hooks_dict:
        _ = settings.pop("hooks", None)
    try:
        _ = path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
# === ANCHOR: HOOK_SETUP_REMOVE_OLD_HOOK_END ===
# === ANCHOR: HOOK_SETUP_END ===
