"""고속 도구(fd, ripgrep) 및 watchdog 자동 설치 유틸리티."""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Callable


def _ask_yn(prompt: str) -> bool:
    """y/N 프롬프트. 터미널이 없으면 False를 반환."""
    try:
        ans = input(prompt).strip().lower()
        return ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def _run_visible(cmd: list[str]) -> bool:
    """명령어를 실행하고 출력을 터미널에 그대로 표시. 성공 여부 반환."""
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


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


def _try_install_homebrew(
    clack_info: Callable,
    clack_warn: Callable,
    clack_success: Callable,
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


def try_install_fast_tools(
    missing_tools: list[str],
    clack_info: Callable,
    clack_warn: Callable,
    clack_success: Callable,
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


def try_install_watchdog(
    clack_info: Callable,
    clack_warn: Callable,
    clack_success: Callable,
) -> None:
    """watchdog이 없을 때 y/N 프롬프트로 설치를 제안."""
    try:
        import watchdog  # noqa: F401
        return
    except ImportError:
        pass

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
