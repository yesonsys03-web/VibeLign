# === ANCHOR: GIT_HOOKS_START ===
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


_HOOK_MARKER = "# vibelign: pre-commit-enforcement v2"
_WINDOWS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


@dataclass(frozen=True)
# === ANCHOR: GIT_HOOKS_HOOKINSTALLRESULT_START ===
class HookInstallResult:
    status: str
    path: Path | None
    detail: str | None = None


# === ANCHOR: GIT_HOOKS_HOOKINSTALLRESULT_END ===


# === ANCHOR: GIT_HOOKS__RUN_GIT_PATH_START ===
def _run_git_path(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            creationflags=_WINDOWS_FLAGS,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


# === ANCHOR: GIT_HOOKS__RUN_GIT_PATH_END ===


# === ANCHOR: GIT_HOOKS_GET_HOOKS_DIR_START ===
def get_hooks_dir(root: Path) -> Path | None:
    hooks_path = _run_git_path(root, "rev-parse", "--git-path", "hooks")
    if not hooks_path:
        return None
    hooks_dir = Path(hooks_path)
    if not hooks_dir.is_absolute():
        hooks_dir = root / hooks_dir
    return hooks_dir


# === ANCHOR: GIT_HOOKS_GET_HOOKS_DIR_END ===


# === ANCHOR: GIT_HOOKS__HOOK_SCRIPT_START ===
def _hook_script(
    preferred_secret_command: str | None, preferred_guard_command: str | None
) -> str:
    commands: list[str] = []
    if preferred_secret_command and preferred_guard_command:
        commands.extend(
            [
                preferred_secret_command,
                "status=$?",
                'if [ "$status" -ne 0 ]; then',
                "  exit $status",
                "fi",
                preferred_guard_command,
                "exit $?",
            ]
        )
    return "\n".join(
        [
            "#!/bin/sh",
            _HOOK_MARKER,
            *commands,
            "if command -v vib >/dev/null 2>&1; then",
            "  vib secrets --staged",
            "  status=$?",
            '  if [ "$status" -ne 0 ]; then',
            "    exit $status",
            "  fi",
            "  vib guard --strict",
            "  exit $?",
            "fi",
            "if command -v vibelign >/dev/null 2>&1; then",
            "  vibelign secrets --staged",
            "  status=$?",
            '  if [ "$status" -ne 0 ]; then',
            "    exit $status",
            "  fi",
            "  vibelign guard --strict",
            "  exit $?",
            "fi",
            'printf "%s\n" "VibeLign pre-commit enforcement could not find `vib` or `vibelign`. Run `vib start` again after fixing PATH." >&2',
            "exit 1",
            "",
        ]
    )


# === ANCHOR: GIT_HOOKS__HOOK_SCRIPT_END ===


# === ANCHOR: GIT_HOOKS_INSTALL_PRE_COMMIT_SECRET_HOOK_START ===
def install_pre_commit_secret_hook(root: Path) -> HookInstallResult:
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)

    vib_path = shutil.which("vib")
    preferred_secret_command = None
    preferred_guard_command = None
    if vib_path:
        preferred_secret_command = f'"{vib_path}" secrets --staged'
        preferred_guard_command = f'"{vib_path}" guard --strict'
    elif sys.executable:
        preferred_secret_command = (
            f'"{sys.executable}" -m vibelign.cli.vib_cli secrets --staged'
        )
        preferred_guard_command = (
            f'"{sys.executable}" -m vibelign.cli.vib_cli guard --strict'
        )

    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8", errors="ignore")
        if _HOOK_MARKER not in existing:
            return HookInstallResult(status="existing-hook", path=hook_path)
        status = "updated"
    else:
        status = "installed"

    _ = hook_path.write_text(
        _hook_script(preferred_secret_command, preferred_guard_command),
        encoding="utf-8",
    )
    if os.name != "nt":
        try:
            current_mode = hook_path.stat().st_mode
            _ = hook_path.chmod(current_mode | 0o755)
        except OSError as exc:
            return HookInstallResult(
                status="chmod-failed", path=hook_path, detail=str(exc)
            )
    return HookInstallResult(status=status, path=hook_path)


# === ANCHOR: GIT_HOOKS_INSTALL_PRE_COMMIT_SECRET_HOOK_END ===


# === ANCHOR: GIT_HOOKS_UNINSTALL_PRE_COMMIT_SECRET_HOOK_START ===
def uninstall_pre_commit_secret_hook(root: Path) -> HookInstallResult:
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)

    hook_path = hooks_dir / "pre-commit"
    if not hook_path.exists():
        return HookInstallResult(status="missing", path=hook_path)

    content = hook_path.read_text(encoding="utf-8", errors="ignore")
    if _HOOK_MARKER not in content:
        return HookInstallResult(status="foreign-hook", path=hook_path)

    hook_path.unlink()
    return HookInstallResult(status="removed", path=hook_path)


# === ANCHOR: GIT_HOOKS_UNINSTALL_PRE_COMMIT_SECRET_HOOK_END ===


# === ANCHOR: GIT_HOOKS_POST_COMMIT_RECORD_START ===
_POST_COMMIT_MARKER = "# vibelign: post-commit-record v1"
_POST_COMMIT_END = "# vibelign: post-commit-record-end"

# vib → vibelign → python -m fallback. stdin 으로 commit 메시지 전달.
_POST_COMMIT_BLOCK_TEMPLATE = """\
{marker}
sha=$(git rev-parse HEAD 2>/dev/null)
msg=$(git log -1 --pretty=%B 2>/dev/null)
if [ -n "$sha" ] && [ -n "$msg" ]; then
    if command -v vib >/dev/null 2>&1; then
        printf "%s" "$msg" | vib _internal_record_commit "$sha" >/dev/null 2>&1 || true
    elif command -v vibelign >/dev/null 2>&1; then
        printf "%s" "$msg" | vibelign _internal_record_commit "$sha" >/dev/null 2>&1 || true
    elif command -v python3 >/dev/null 2>&1; then
        printf "%s" "$msg" | python3 -m vibelign.cli.vib_cli _internal_record_commit "$sha" >/dev/null 2>&1 || true
    fi
fi
{end}
"""


def _build_post_commit_block() -> str:
    return _POST_COMMIT_BLOCK_TEMPLATE.format(
        marker=_POST_COMMIT_MARKER, end=_POST_COMMIT_END
    )


def install_post_commit_record_hook(root: Path) -> HookInstallResult:
    """Vibelign 블록을 PREPEND 해서 기존 hook 의 exit 와 무관하게 실행되게 한다."""
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)
    hook_path = hooks_dir / "post-commit"
    block = _build_post_commit_block()

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if _POST_COMMIT_MARKER in existing:
            return HookInstallResult(status="already-installed", path=hook_path)
        # shebang 보존 + 그 다음에 vibelign 블록 + 그 다음에 기존 본문
        if existing.startswith("#!"):
            shebang, _, rest = existing.partition("\n")
            new_content = f"{shebang}\n\n{block}\n{rest}"
        else:
            new_content = f"#!/bin/sh\n\n{block}\n{existing}"
    else:
        new_content = f"#!/bin/sh\n\n{block}\n"

    hook_path.write_text(new_content, encoding="utf-8")
    hook_path.chmod(0o755)
    return HookInstallResult(status="installed", path=hook_path)


def uninstall_post_commit_record_hook(root: Path) -> HookInstallResult:
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)
    hook_path = hooks_dir / "post-commit"
    if not hook_path.exists():
        return HookInstallResult(status="missing", path=hook_path)

    content = hook_path.read_text(encoding="utf-8")
    if _POST_COMMIT_MARKER not in content:
        return HookInstallResult(status="foreign-hook", path=hook_path)

    start = content.index(_POST_COMMIT_MARKER)
    end_idx = content.index(_POST_COMMIT_END, start) + len(_POST_COMMIT_END)
    # 양 옆 최대 1개 newline 만 소비 (shebang/본문 보존)
    if start > 0 and content[start - 1] == "\n":
        start -= 1
    if end_idx < len(content) and content[end_idx] == "\n":
        end_idx += 1
    new_content = content[:start] + content[end_idx:]
    new_content = new_content.rstrip()

    if new_content.strip() in ("", "#!/bin/sh"):
        hook_path.unlink()
        return HookInstallResult(status="removed", path=hook_path)

    hook_path.write_text(new_content + "\n", encoding="utf-8")
    return HookInstallResult(status="removed", path=hook_path)
# === ANCHOR: GIT_HOOKS_POST_COMMIT_RECORD_END ===
# === ANCHOR: GIT_HOOKS_END ===
