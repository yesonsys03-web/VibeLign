from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


_HOOK_MARKER = "# vibelign: secrets-pre-commit v1"


@dataclass(frozen=True)
class HookInstallResult:
    status: str
    path: Path | None
    detail: str | None = None


def _run_git_path(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def get_hooks_dir(root: Path) -> Path | None:
    hooks_path = _run_git_path(root, "rev-parse", "--git-path", "hooks")
    if not hooks_path:
        return None
    hooks_dir = Path(hooks_path)
    if not hooks_dir.is_absolute():
        hooks_dir = root / hooks_dir
    return hooks_dir


def _hook_script(preferred_command: str | None) -> str:
    commands = []
    if preferred_command:
        commands.extend([f"if {preferred_command}; then", "  exit 0", "fi"])
    return "\n".join(
        [
            "#!/bin/sh",
            _HOOK_MARKER,
            *commands,
            "if command -v vib >/dev/null 2>&1; then",
            "  vib secrets --staged",
            "  exit $?",
            "fi",
            "if command -v vibelign >/dev/null 2>&1; then",
            "  vibelign secrets --staged",
            "  exit $?",
            "fi",
            'printf "%s\n" "VibeLign secret protection could not find `vib` or `vibelign`. Run `vib start` again after fixing PATH." >&2',
            "exit 1",
            "",
        ]
    )


def install_pre_commit_secret_hook(root: Path) -> HookInstallResult:
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)

    vib_path = shutil.which("vib")
    preferred_command = None
    if vib_path:
        preferred_command = f'"{vib_path}" secrets --staged >/dev/null 2>&1'
    elif sys.executable:
        preferred_command = (
            f'"{sys.executable}" -m vibelign.vib_cli secrets --staged >/dev/null 2>&1'
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

    hook_path.write_text(_hook_script(preferred_command), encoding="utf-8")
    if os.name != "nt":
        try:
            current_mode = hook_path.stat().st_mode
            _ = hook_path.chmod(current_mode | 0o755)
        except OSError as exc:
            return HookInstallResult(
                status="chmod-failed", path=hook_path, detail=str(exc)
            )
    return HookInstallResult(status=status, path=hook_path)


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
