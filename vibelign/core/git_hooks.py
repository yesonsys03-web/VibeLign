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
# === ANCHOR: GIT_HOOKS_END ===
