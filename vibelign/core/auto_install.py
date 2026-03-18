# === ANCHOR: AUTO_INSTALL_START ===
"""고속 도구(fd, ripgrep) 및 watchdog 자동 설치 유틸리티."""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Callable


# === ANCHOR: AUTO_INSTALL__ASK_YN_START ===
def _ask_yn(prompt: str) -> bool:
    """y/N 프롬프트. 터미널이 없으면 False를 반환."""
    try:
        ans = input(prompt).strip().lower()
        return ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False
# === ANCHOR: AUTO_INSTALL__ASK_YN_END ===


# === ANCHOR: AUTO_INSTALL__RUN_VISIBLE_START ===
def _run_visible(cmd: list[str]) -> bool:
    """명령어를 실행하고 출력을 터미널에 그대로 표시. 성공 여부 반환."""
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False
# === ANCHOR: AUTO_INSTALL__RUN_VISIBLE_END ===


# === ANCHOR: AUTO_INSTALL__DETECT_PKG_MANAGER_START ===
def _detect_pkg_manager() -> str | None:
    """현재 시스템에서 사용 가능한 패키지 관리자를 감지.

    반환값:
        "brew"        — Mac, brew 설치됨
        "brew_missing" — Mac, brew 없음
        "winget"      — Windows
        "apt" / "dnf" / "pacman" — Linux
        None          — 알 수 없음
    """
    if sys.platform == "darwin":
        return "brew" if shutil.which("brew") else "brew_missing"
    if sys.platform == "win32":
        return "winget" if shutil.which("winget") else None
    for mgr in ("apt", "dnf", "pacman"):
        if shutil.which(mgr):
            return mgr
    return None
# === ANCHOR: AUTO_INSTALL__DETECT_PKG_MANAGER_END ===


# === ANCHOR: AUTO_INSTALL__INSTALL_CMD_START ===
def _install_cmd(pkg_manager: str, tools: list[str]) -> list[str] | None:
    """패키지 관리자별 설치 명령어를 반환. 설치할 게 없으면 None."""
    has_fd = "fd" in tools
    has_rg = any(t in tools for t in ("rg", "rg (ripgrep)", "ripgrep"))

    if pkg_manager == "brew":
        pkgs = (["fd"] if has_fd else []) + (["ripgrep"] if has_rg else [])
        return ["brew", "install"] + pkgs if pkgs else None

    if pkg_manager == "winget":
        pkgs = (["sharkdp.fd"] if has_fd else []) + (["BurntSushi.ripgrep.MSVC"] if has_rg else [])
        return ["winget", "install"] + pkgs if pkgs else None

    if pkg_manager in ("apt", "dnf"):
        pkgs = (["fd-find"] if has_fd else []) + (["ripgrep"] if has_rg else [])
        installer = "apt" if pkg_manager == "apt" else "dnf"
        return ["sudo", installer, "install", "-y"] + pkgs if pkgs else None

    if pkg_manager == "pacman":
        pkgs = (["fd"] if has_fd else []) + (["ripgrep"] if has_rg else [])
        return ["sudo", "pacman", "-S", "--noconfirm"] + pkgs if pkgs else None

    return None
# === ANCHOR: AUTO_INSTALL__INSTALL_CMD_END ===


# === ANCHOR: AUTO_INSTALL__TRY_INSTALL_HOMEBREW_START ===
def _try_install_homebrew(
    clack_info: Callable,
    clack_warn: Callable,
    clack_success: Callable,
# === ANCHOR: AUTO_INSTALL__TRY_INSTALL_HOMEBREW_END ===
) -> bool:
    """Mac에 Homebrew가 없을 때 설치를 제안. 성공 여부 반환."""
    clack_warn("Homebrew(Mac 패키지 관리자)가 설치되어 있지 않아요.")
    clack_info("  fd와 ripgrep을 설치하려면 Homebrew가 먼저 필요해요.")
    clack_info('  설치 명령어: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')

    if not _ask_yn("  지금 Homebrew를 설치할까요? [y/N] "):
        clack_info("건너뜀. 나중에 https://brew.sh 에서 설치하세요.")
        return False

    clack_info("Homebrew 설치 중... (시간이 좀 걸릴 수 있어요)")
    ok = _run_visible([
        "/bin/bash", "-c",
        "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)",
    ])
    if ok and shutil.which("brew"):
        clack_success("Homebrew 설치 완료!")
        return True
    clack_warn("Homebrew 설치에 실패했어요. https://brew.sh 를 직접 방문해서 설치하세요.")
    return False


# === ANCHOR: AUTO_INSTALL_TRY_INSTALL_FAST_TOOLS_START ===
def try_install_fast_tools(
    missing_tools: list[str],
    clack_info: Callable,
    clack_warn: Callable,
    clack_success: Callable,
# === ANCHOR: AUTO_INSTALL_TRY_INSTALL_FAST_TOOLS_END ===
) -> None:
    """fd/ripgrep이 없을 때 y/N 프롬프트로 설치를 제안."""
    if not missing_tools:
        return

    tool_names = ", ".join(missing_tools)
    clack_info(f"⚡ {tool_names} 이(가) 설치되어 있지 않아요.")
    clack_info("  설치하면 파일 스캔 속도가 크게 빨라져요. (없어도 정상 작동해요)")

    pkg_manager = _detect_pkg_manager()

    if pkg_manager == "brew_missing":
        if not _try_install_homebrew(clack_info, clack_warn, clack_success):
            return
        pkg_manager = "brew" if shutil.which("brew") else None

    if pkg_manager is None:
        clack_warn("자동 설치를 지원하지 않는 환경이에요.")
        clack_info("  직접 설치: https://github.com/sharkdp/fd  /  https://github.com/BurntSushi/ripgrep")
        return

    cmd = _install_cmd(pkg_manager, missing_tools)
    if not cmd:
        return

    cmd_str = " ".join(cmd)
    if not _ask_yn(f"  지금 설치할까요? ({cmd_str}) [y/N] "):
        clack_info("건너뜀. 'vib install' 가이드를 참고하세요.")
        return

    clack_info(f"설치 중... ({cmd_str})")
    ok = _run_visible(cmd)
    if ok:
        clack_success(f"{tool_names} 설치 완료!")
    else:
        clack_warn(f"설치에 실패했어요. 터미널에서 직접 실행해 보세요: {cmd_str}")


# === ANCHOR: AUTO_INSTALL_ENSURE_PYPROJECT_START ===
def ensure_pyproject_toml(
    root,
    clack_info: Callable,
    clack_warn: Callable,
    clack_success: Callable,
) -> bool:
    """pyproject.toml이 없으면 y/N 프롬프트로 생성을 제안. 생성하면 True 반환."""
    from pathlib import Path
    pyproject_path = Path(root) / "pyproject.toml"
    if pyproject_path.exists():
        return False

    clack_info("📦 pyproject.toml 파일이 없어요.")
    clack_info("  이 파일이 없으면 uv run 으로 파이썬 파일을 실행할 수 없어요.")
    if not _ask_yn("  지금 기본 파일을 만들까요? [y/N] "):
        clack_info("건너뜀. 나중에 pyproject.toml을 직접 만들거나 `uv init`으로 생성하세요.")
        return False

    # 폴더명을 프로젝트명으로 사용 (공백·특수문자 → 하이픈)
    import re
    folder_name = Path(root).name
    project_name = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", folder_name).strip("-") or "my-project"

    # uv / pip 둘 다 호환되는 최소 pyproject.toml
    content = f"""[project]
name = "{project_name}"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []
"""
    pyproject_path.write_text(content, encoding="utf-8")
    clack_success(f"pyproject.toml 생성 완료! (프로젝트명: {project_name})")
    return True
# === ANCHOR: AUTO_INSTALL_ENSURE_PYPROJECT_END ===


# === ANCHOR: AUTO_INSTALL_TRY_INSTALL_WATCHDOG_START ===
def try_install_watchdog(
    clack_info: Callable,
    clack_warn: Callable,
    clack_success: Callable,
# === ANCHOR: AUTO_INSTALL_TRY_INSTALL_WATCHDOG_END ===
) -> None:
    """watchdog이 없을 때 y/N 프롬프트로 설치를 제안."""
    try:
        import watchdog  # noqa: F401
        return
    except ImportError:
        pass

    # uv tool 환경은 pip이 없으므로 uv pip --python 으로 설치
    # 일반 Python 환경은 sys.executable -m pip 사용
    if shutil.which("uv"):
        cmd = ["uv", "pip", "install", "--python", sys.executable, "watchdog"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "watchdog"]
    clack_info("⚡ watchdog 이(가) 설치되어 있지 않아요.")
    clack_info("  설치하면 vib watch 로 파일 변경을 실시간 감지할 수 있어요. (없어도 정상 작동해요)")
    if not _ask_yn(f"  지금 설치할까요? ({' '.join(cmd)}) [y/N] "):
        clack_info("건너뜀. 나중에 `pip install watchdog`으로 설치하세요.")
        return
    clack_info(f"설치 중... ({' '.join(cmd)})")
    ok = _run_visible(cmd)
    if ok:
        clack_success("watchdog 설치 완료!")
    else:
        clack_warn("설치에 실패했어요. `pip install watchdog`을 직접 실행하세요.")
# === ANCHOR: AUTO_INSTALL_END ===
