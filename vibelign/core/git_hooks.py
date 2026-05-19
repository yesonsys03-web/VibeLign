# === ANCHOR: GIT_HOOKS_START ===
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS

_HOOK_MARKER = "# vibelign: pre-commit-enforcement v3"
# v1/v2 그리고 v2 이전의 secrets-pre-commit v1 까지 인식해야 기존 설치본을 자동 교체할 수 있다.
_HOOK_MARKER_RE = re.compile(
    r"# vibelign: (?:pre-commit-enforcement v[123]|secrets-pre-commit v1)"
)
_GUARD_ADVISORY_MSG = (
    "VibeLign: vib guard --strict reported issues (exit $guard_status). "
    "Commit allowed; rerun 'vib guard --strict' to fix, "
    "or set VIBELIGN_STRICT_GUARD=1 to block commits on guard failures."
)


def _secret_then_guard(secret_cmd: str, guard_cmd: str, indent: str) -> list[str]:
    """secrets 는 차단, guard 는 기본 advisory (VIBELIGN_STRICT_GUARD=1 일 때만 차단)."""
    return [
        f"{indent}{secret_cmd}",
        f"{indent}status=$?",
        f'{indent}if [ "$status" -ne 0 ]; then',
        f"{indent}  exit $status",
        f"{indent}fi",
        f"{indent}{guard_cmd}",
        f"{indent}guard_status=$?",
        f'{indent}if [ "$guard_status" -ne 0 ]; then',
        f'{indent}  if [ -n "$VIBELIGN_STRICT_GUARD" ]; then',
        f"{indent}    exit $guard_status",
        f"{indent}  fi",
        f'{indent}  printf "%s\\n" "{_GUARD_ADVISORY_MSG}" >&2',
        f"{indent}fi",
        f"{indent}exit 0",
    ]


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
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
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
    lines: list[str] = [
        "#!/bin/sh",
        _HOOK_MARKER,
        'if [ -n "$VIBELIGN_SKIP_HOOK" ]; then',
        "  exit 0",
        "fi",
    ]
    if preferred_secret_command and preferred_guard_command:
        lines.extend(
            _secret_then_guard(
                preferred_secret_command, preferred_guard_command, indent=""
            )
        )
    lines.append("if command -v vib >/dev/null 2>&1; then")
    lines.extend(
        _secret_then_guard("vib secrets --staged", "vib guard --strict", indent="  ")
    )
    lines.append("fi")
    lines.append("if command -v vibelign >/dev/null 2>&1; then")
    lines.extend(
        _secret_then_guard(
            "vibelign secrets --staged", "vibelign guard --strict", indent="  "
        )
    )
    lines.append("fi")
    lines.extend(
        [
            'printf "%s\\n" "VibeLign pre-commit enforcement could not find `vib` or `vibelign`. Run `vib start` again after fixing PATH." >&2',
            "exit 1",
            "",
        ]
    )
    return "\n".join(lines)


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
        if not _HOOK_MARKER_RE.search(existing):
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
    if not _HOOK_MARKER_RE.search(content):
        return HookInstallResult(status="foreign-hook", path=hook_path)

    hook_path.unlink()
    return HookInstallResult(status="removed", path=hook_path)


# === ANCHOR: GIT_HOOKS_UNINSTALL_PRE_COMMIT_SECRET_HOOK_END ===


# === ANCHOR: GIT_HOOKS_POST_COMMIT_RECORD_START ===
_POST_COMMIT_MARKER_V4 = "# vibelign: post-commit-record v4"
_POST_COMMIT_END = "# vibelign: post-commit-record-end"
_POST_COMMIT_MARKER_RE = re.compile(r"# vibelign: post-commit-record v[1234]")

# v4 (2026-05-19): install 시점에 shutil.which('vib') / shutil.which('vibelign') /
# sys.executable 절대 경로를 캡처해 hook 에 박는다. GUI tool (Sourcetree, VS Code 등)
# 에서 commit 할 때 PATH 가 빈약해 `command -v vib` 가 false 가 되던 케이스에서
# 자동 백업이 누락되던 회귀를 막는다. PATH 기반 fallback (uv/python/python3/vib/vibelign/py)
# 은 그대로 두어 사용자가 vib 를 PATH 옮기거나 재설치한 경우에도 동작.
_POST_COMMIT_BLOCK_TEMPLATE = """\
{marker}
sha=$(git rev-parse HEAD 2>/dev/null)
msg=$(git log -1 --pretty=%B 2>/dev/null)
if [ -n "$sha" ] && [ -n "$msg" ]; then
    vibelign_post_commit_done=0
{absolute_branches}\
    if [ "$vibelign_post_commit_done" -eq 0 ] && command -v uv >/dev/null 2>&1; then
        printf "%s" "$msg" | VIBELIGN_REQUIRE_RUST_CHECKPOINT=1 uv run python -m vibelign.cli.vib_cli _internal_post_commit "$sha" >/dev/null && vibelign_post_commit_done=1
    fi
    if [ "$vibelign_post_commit_done" -eq 0 ] && command -v python >/dev/null 2>&1; then
        printf "%s" "$msg" | VIBELIGN_REQUIRE_RUST_CHECKPOINT=1 python -m vibelign.cli.vib_cli _internal_post_commit "$sha" >/dev/null && vibelign_post_commit_done=1
    fi
    if [ "$vibelign_post_commit_done" -eq 0 ] && command -v python3 >/dev/null 2>&1; then
        printf "%s" "$msg" | VIBELIGN_REQUIRE_RUST_CHECKPOINT=1 python3 -m vibelign.cli.vib_cli _internal_post_commit "$sha" >/dev/null && vibelign_post_commit_done=1
    fi
    if [ "$vibelign_post_commit_done" -eq 0 ] && command -v vib >/dev/null 2>&1; then
        printf "%s" "$msg" | VIBELIGN_REQUIRE_RUST_CHECKPOINT=1 vib _internal_post_commit "$sha" >/dev/null && vibelign_post_commit_done=1
    fi
    if [ "$vibelign_post_commit_done" -eq 0 ] && command -v vibelign >/dev/null 2>&1; then
        printf "%s" "$msg" | VIBELIGN_REQUIRE_RUST_CHECKPOINT=1 vibelign _internal_post_commit "$sha" >/dev/null && vibelign_post_commit_done=1
    fi
    if [ "$vibelign_post_commit_done" -eq 0 ] && command -v py >/dev/null 2>&1; then
        printf "%s" "$msg" | VIBELIGN_REQUIRE_RUST_CHECKPOINT=1 py -3 -m vibelign.cli.vib_cli _internal_post_commit "$sha" >/dev/null && vibelign_post_commit_done=1
    fi
fi
{end}
"""


def _absolute_path_branch(command: str) -> str:
    return (
        '    if [ "$vibelign_post_commit_done" -eq 0 ] '
        f"&& [ -x {command.split()[0]} ]; then\n"
        f'        printf "%s" "$msg" | VIBELIGN_REQUIRE_RUST_CHECKPOINT=1 {command} '
        '_internal_post_commit "$sha" >/dev/null && vibelign_post_commit_done=1\n'
        "    fi\n"
    )


def _collect_absolute_branches() -> str:
    """Install 시점에 PATH 에서 찾은 vib/vibelign 절대경로를 hook 에 박는다.

    Why: GUI commit tool (Sourcetree, VS Code, Tower) 은 launchd PATH 만 상속해
    `~/.local/bin` 이 없는 경우가 흔하다. `command -v vib` 가 false → fallback 5개
    전부 fail → 자동 백업 누락. install 시점에 캡처한 절대 경로를 최우선 fallback 으로
    두면 PATH 환경 차이를 우회할 수 있다.
    """
    branches: list[str] = []
    for tool_name in ("vib", "vibelign"):
        resolved = shutil.which(tool_name)
        if resolved:
            branches.append(_absolute_path_branch(f'"{resolved}"'))
    if sys.executable:
        branches.append(
            _absolute_path_branch(f'"{sys.executable}" -m vibelign.cli.vib_cli')
        )
    return "".join(branches)


def _build_post_commit_block() -> str:
    return _POST_COMMIT_BLOCK_TEMPLATE.format(
        marker=_POST_COMMIT_MARKER_V4,
        end=_POST_COMMIT_END,
        absolute_branches=_collect_absolute_branches(),
    )


def _strip_post_commit_block(content: str) -> tuple[str, bool]:
    marker_match = _POST_COMMIT_MARKER_RE.search(content)
    if marker_match is None:
        return content, False
    end = content.find(_POST_COMMIT_END, marker_match.start())
    if end < 0:
        return content, False
    start = marker_match.start()
    end_idx = end + len(_POST_COMMIT_END)
    if start > 0 and content[start - 1] == "\n":
        start -= 1
    if end_idx < len(content) and content[end_idx] == "\n":
        end_idx += 1
    return content[:start] + content[end_idx:], True


def _with_newline_style(text: str, existing: str) -> str:
    return text.replace("\n", "\r\n") if "\r\n" in existing else text


def _read_hook_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="ignore")


def install_post_commit_record_hook(root: Path) -> HookInstallResult:
    """Vibelign 블록을 PREPEND 해서 기존 hook 의 exit 와 무관하게 실행되게 한다."""
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)
    hook_path = hooks_dir / "post-commit"
    block = _build_post_commit_block()

    if hook_path.exists():
        original_mode = hook_path.stat().st_mode
        existing = _read_hook_text(hook_path)
        stripped, had_block = _strip_post_commit_block(existing)
        if had_block and block in existing:
            return HookInstallResult(status="already-installed", path=hook_path)
        status = "updated" if had_block else "installed"
        existing = stripped
        # shebang 보존 + 그 다음에 vibelign 블록 + 그 다음에 기존 본문
        if existing.startswith("#!"):
            shebang, _, rest = existing.partition("\n")
            new_content = f"{shebang}\n\n{block}\n{rest}"
        else:
            new_content = f"#!/bin/sh\n\n{block}\n{existing}"
        new_content = _with_newline_style(new_content, existing)
    else:
        original_mode = 0o755
        status = "installed"
        new_content = f"#!/bin/sh\n\n{block}\n"

    hook_path.write_text(new_content, encoding="utf-8")
    hook_path.chmod(original_mode)
    return HookInstallResult(status=status, path=hook_path)


def uninstall_post_commit_record_hook(root: Path) -> HookInstallResult:
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)
    hook_path = hooks_dir / "post-commit"
    if not hook_path.exists():
        return HookInstallResult(status="missing", path=hook_path)

    content = _read_hook_text(hook_path)
    new_content, had_block = _strip_post_commit_block(content)
    if not had_block:
        return HookInstallResult(status="foreign-hook", path=hook_path)
    new_content = new_content.rstrip()

    if new_content.strip() in ("", "#!/bin/sh"):
        hook_path.unlink()
        return HookInstallResult(status="removed", path=hook_path)

    suffix = "\r\n" if "\r\n" in content else "\n"
    hook_path.write_text(_with_newline_style(new_content, content) + suffix, encoding="utf-8")
    return HookInstallResult(status="removed", path=hook_path)
# === ANCHOR: GIT_HOOKS_POST_COMMIT_RECORD_END ===
# === ANCHOR: GIT_HOOKS_END ===
