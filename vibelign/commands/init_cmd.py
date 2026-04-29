# === ANCHOR: INIT_CMD_START ===
import platform
import shutil
import subprocess
import sys
from argparse import Namespace
from collections.abc import Sequence
from pathlib import Path

from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS


from vibelign.terminal_render import (
    clack_error,
    clack_info,
    clack_intro,
    clack_outro,
    clack_step,
    clack_success,
    clack_warn,
    cli_print,
)

print = cli_print

_MIN_PYTHON = (3, 9)

_ERR = {
    "network": (
        "인터넷 연결이 필요해요.\n    와이파이가 연결됐는지 확인하고 다시 해보세요."
    ),
    "permission": (
        "이 컴퓨터에 설치할 권한이 없어요.\n"
        "    Mac/Linux: sudo vib init\n"
        "    Windows:   관리자 권한으로 터미널을 열고 다시 시도해보세요."
    ),
    "pip_broken": (
        "Python이 제대로 설치되지 않은 것 같아요.\n"
        "    python.org 에서 Python을 다시 설치해보세요."
    ),
    "uv_fail": (
        "uv 설치에 실패했어요.\n"
        "    직접 설치하려면: https://docs.astral.sh/uv/getting-started/installation/"
    ),
    "reinstall_fail": (
        "vibelign 재설치에 실패했어요.\n"
        "    직접 설치하려면:\n"
        "      uv:  uv tool install vibelign --no-cache\n"
        "      pip: pip install vibelign --upgrade --no-cache-dir"
    ),
}

_UV_INSTALL_CMD = {
    "Darwin": "curl -LsSf https://astral.sh/uv/install.sh | sh",
    "Linux": "curl -LsSf https://astral.sh/uv/install.sh | sh",
    "Windows": (
        "powershell -ExecutionPolicy ByPass -c "
        '"irm https://astral.sh/uv/install.ps1 | iex"'
    ),
}


def _run_text_subprocess(
    cmd: Sequence[str] | str,
    *,
    shell: bool = False,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=shell,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=WINDOWS_SUBPROCESS_FLAGS,
    )


# === ANCHOR: INIT_CMD__OK_START ===
def _ok(msg: str) -> None:
    clack_success(msg)


# === ANCHOR: INIT_CMD__OK_END ===


# === ANCHOR: INIT_CMD__STEP_START ===
def _step(msg: str) -> None:
    clack_step(msg)


# === ANCHOR: INIT_CMD__STEP_END ===


# === ANCHOR: INIT_CMD__WARN_START ===
def _warn(msg: str) -> None:
    clack_warn(msg)


# === ANCHOR: INIT_CMD__WARN_END ===


# === ANCHOR: INIT_CMD__FAIL_START ===
def _fail(msg: str) -> None:
    clack_error(msg)


# === ANCHOR: INIT_CMD__FAIL_END ===


# === ANCHOR: INIT_CMD__KOREAN_ERROR_START ===
def _korean_error(result: subprocess.CompletedProcess[str]) -> str:
    combined = ((result.stdout or "") + (result.stderr or "")).lower()
    if any(
        k in combined
        for k in ["network", "connection", "timeout", "urlopen", "unreachable"]
    ):
        return _ERR["network"]
    if any(k in combined for k in ["permission", "access denied", "denied"]):
        return _ERR["permission"]
    return ""


# === ANCHOR: INIT_CMD__KOREAN_ERROR_END ===


# === ANCHOR: INIT_CMD__CHECK_PYTHON_START ===
def _check_python() -> bool:
    cur = sys.version_info[:2]
    if cur < _MIN_PYTHON:
        _fail(
            f"Python {cur[0]}.{cur[1]} 이에요. {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]} 이상이 필요해요."
        )
        clack_info("python.org 에서 최신 Python을 설치해보세요.")
        return False
    _ok(f"Python {cur[0]}.{cur[1]}")
    return True


# === ANCHOR: INIT_CMD__CHECK_PYTHON_END ===


# === ANCHOR: INIT_CMD__CHECK_PIP_START ===
def _check_pip() -> bool:
    if shutil.which("pip") or shutil.which("pip3"):
        _ok("pip")
        return True
    _warn("pip이 없어요. Python 내장 기능으로 복구를 시도할게요...")
    result = _run_text_subprocess(
        [sys.executable, "-m", "ensurepip", "--upgrade"],
    )
    if result.returncode == 0:
        _ok("pip 복구 완료")
        return True
    _fail("pip 복구에 실패했어요.")
    print(f"    {_ERR['pip_broken']}")
    return False


# === ANCHOR: INIT_CMD__CHECK_PIP_END ===


# === ANCHOR: INIT_CMD__CHECK_UV_START ===
def _check_uv() -> bool:
    """uv 감지. 없으면 설치 여부를 물어봄. 현재 세션에서 사용 가능하면 True."""
    if shutil.which("uv"):
        _ok("uv")
        return True

    _warn("uv가 없어요.")
    print("    uv를 설치하면 더 빠르고 안정적으로 패키지를 관리할 수 있어요.")
    try:
        answer = input("    uv를 설치할까요? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        _step("uv 설치를 건너뜁니다. pip으로 진행할게요.")
        return False

    if answer not in {"y", "yes", "ㅇ"}:
        _step("uv 설치를 건너뜁니다. pip으로 진행할게요.")
        return False

    system = platform.system()
    cmd = _UV_INSTALL_CMD.get(system)
    if not cmd:
        _fail(f"지원하지 않는 운영체제예요: {system}")
        return False

    _step("uv를 설치하는 중...")
    result = _run_text_subprocess(cmd, shell=True)
    if result.returncode != 0:
        _fail("uv 설치에 실패했어요.")
        hint = _korean_error(result)
        clack_info(hint or _ERR["uv_fail"])
        return False

    # 설치 후 현재 세션 PATH 반영 여부 확인
    if shutil.which("uv"):
        _ok("uv 설치 완료")
        return True

    # 설치는 됐지만 새 터미널에서만 PATH 적용
    _uv_candidates = [
        Path.home() / ".local" / "bin" / "uv",
        Path.home() / ".cargo" / "bin" / "uv",
    ]
    if any(p.exists() for p in _uv_candidates):
        _ok("uv 설치 완료 (새 터미널에서 PATH가 적용돼요)")
        _step("이번 재설치는 pip으로 진행할게요.")
        return False

    _fail("uv 설치 경로를 찾을 수 없어요. pip으로 진행할게요.")
    return False


# === ANCHOR: INIT_CMD__CHECK_UV_END ===


# === ANCHOR: INIT_CMD__FIND_SOURCE_ROOT_START ===
def _find_source_root() -> "Path | None":
    """vibelign 소스 루트 디렉토리를 감지합니다 (개발 환경용)."""
    # 1) 현재 파일 기준 상위로 올라가며 pyproject.toml 탐색 (editable install)
    import vibelign as _pkg

    for candidate in Path(_pkg.__file__).parents:
        if (candidate / "pyproject.toml").exists() and (
            candidate / "vibelign"
        ).is_dir():
            return candidate
    # 2) 잘 알려진 개발 경로 직접 확인
    for known in [
        Path.home() / "coding" / "VibeLign",
        Path.cwd(),
    ]:
        if (known / "pyproject.toml").exists() and (known / "vibelign").is_dir():
            return known
    return None


# === ANCHOR: INIT_CMD__FIND_SOURCE_ROOT_END ===


# === ANCHOR: INIT_CMD__REINSTALL_LOCAL_START ===
def _reinstall_local(source_root: Path) -> bool:
    """네트워크 없이 소스 디렉토리에서 직접 복사해 설치합니다."""
    import importlib
    import vibelign as _pkg

    dest = Path(_pkg.__file__).parent
    src = source_root / "vibelign"
    _step(f"로컬 소스에서 복사 중: {src} → {dest}")
    if dest.resolve() == src.resolve():
        _ok("이미 로컬 소스에서 실행 중이에요 (editable install)")
        return True
    try:
        import shutil

        _ = shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
        # .pyc 캐시 무효화
        for pyc in dest.rglob("*.pyc"):
            pyc.unlink(missing_ok=True)
        importlib.invalidate_caches()
        _ok("로컬 소스 복사 완료")
        return True
    except Exception as e:
        _fail(f"복사 실패: {e}")
        return False


# === ANCHOR: INIT_CMD__REINSTALL_LOCAL_END ===


# === ANCHOR: INIT_CMD__REINSTALL_START ===
def _reinstall(use_uv: bool, force: bool) -> bool:
    # 로컬 소스가 감지되면 네트워크 없이 직접 복사
    source_root = _find_source_root()
    if source_root is not None:
        _ok(f"로컬 소스 감지: {source_root}")
        return _reinstall_local(source_root)

    if use_uv:
        _step("uv 캐시를 정리하는 중...")
        try:
            _ = subprocess.run(
                ["uv", "cache", "clean"], capture_output=True, timeout=15
            )
        except subprocess.TimeoutExpired:
            _warn("uv 캐시 정리 시간 초과 — 건너뜁니다.")
        cmd = ["uv", "tool", "install", "vibelign", "--no-cache"]
        if force:
            cmd.append("--force")
        _step("vibelign 재설치 중 (uv)...")
    else:
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "vibelign",
            "--upgrade",
            "--no-cache-dir",
        ]
        if force:
            cmd.append("--force-reinstall")
        _step("vibelign 재설치 중 (pip)...")

    try:
        result = _run_text_subprocess(cmd, timeout=120)
    except subprocess.TimeoutExpired:
        _fail("vibelign 재설치가 너무 오래 걸려 중단됐어요.")
        clack_info("인터넷 연결 상태를 확인하고 다시 시도해보세요.")
        return False

    if result.returncode == 0:
        combined = (result.stdout or "") + (result.stderr or "")
        already = any(
            k in combined.lower()
            for k in ["already installed", "up-to-date", "up to date", "satisfied"]
        )
        if already and not force:
            _ok("이미 최신 버전이에요")
            clack_info("강제로 다시 설치하려면: vib init --force")
        else:
            _ok("vibelign 재설치 완료")
        return True

    _fail("vibelign 재설치에 실패했어요.")
    hint = _korean_error(result)
    clack_info(hint or _ERR["reinstall_fail"])
    return False


# === ANCHOR: INIT_CMD__REINSTALL_END ===


# === ANCHOR: INIT_CMD_RUN_INIT_START ===
def run_init(args: Namespace) -> None:
    force = bool(getattr(args, "force", False))

    clack_intro("VibeLign 업데이트 / 재설치")

    clack_step("1/4 Python 버전 확인")
    if not _check_python():
        return

    clack_step("2/4 pip 확인")
    if not _check_pip():
        return

    clack_step("3/4 uv 확인")
    uv_ready = _check_uv()

    clack_step("4/4 vibelign 재설치")
    success = _reinstall(use_uv=uv_ready, force=force)

    if success:
        clack_outro("설치가 끝났어요")
        clack_info("지금 터미널을 닫고 새로 열어야 새 버전이 적용돼요.")
        clack_info("그 다음: vib start")
    else:
        clack_error("재설치 중 문제가 생겼어요.")
        clack_info("위의 안내를 따라 해결해보세요.")


# === ANCHOR: INIT_CMD_RUN_INIT_END ===
# === ANCHOR: INIT_CMD_END ===
