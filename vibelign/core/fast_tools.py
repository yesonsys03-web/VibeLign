# === ANCHOR: FAST_TOOLS_START ===
"""고속 파일 탐색 + 앵커 스캔 래퍼.

fd / rg 가 설치되어 있으면 사용하고, 없으면 Python 폴백으로 투명하게 작동.
기능 차이는 없고 속도 차이만 있다.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from vibelign.core.structure_policy import SCAN_IGNORED_DIRS, SOURCE_FILE_SUFFIXES

_WINDOWS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

_ANCHOR_RE = re.compile(r"ANCHOR:\s*([A-Z0-9_]+)")

# 모듈 로드 시 한 번만 체크 (Ubuntu는 fd 대신 fdfind 로 설치됨)
_FD: str | None = shutil.which("fd") or shutil.which("fdfind")
_RG: str | None = shutil.which("rg")

_FD_EXCLUDES = list(sorted(SCAN_IGNORED_DIRS))

_SOURCE_EXTS = list(SOURCE_FILE_SUFFIXES)


def has_fd() -> bool:
    return _FD is not None


def has_rg() -> bool:
    return _RG is not None


def _run_text_command(cmd: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            creationflags=_WINDOWS_FLAGS,
        )
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        UnicodeDecodeError,
    ):
        return None


def find_source_files_fd(root: Path) -> list[Path]:
    """fd로 소스 파일 목록을 반환. 실패 시 빈 리스트 (Python 폴백 신호)."""
    if _FD is None:
        return []
    cmd: list[str] = [_FD, "--type", "f"]
    for ext in _SOURCE_EXTS:
        cmd += ["-e", ext]
    for excl in _FD_EXCLUDES:
        cmd += ["--exclude", excl]
    cmd += [".", str(root)]
    result = _run_text_command(cmd)
    if result is None or result.returncode != 0:
        return []
    return [Path(line) for line in (result.stdout or "").splitlines() if line.strip()]


def grep_anchors_rg(root: Path) -> dict[str, list[str]] | None:
    """rg로 전체 프로젝트 앵커를 한 번에 스캔.

    반환: {rel_path: [anchor_base_names]}
    실패 시 None → 호출부에서 Python 폴백으로 전환.
    """
    glob_args: list[str] = []
    for ext in _SOURCE_EXTS:
        glob_args += ["--glob", f"*.{ext}"]
    for ignored in _FD_EXCLUDES:
        glob_args += ["--glob", f"!{ignored}/**"]

    if _RG is None:
        return None

    cmd: list[str] = (
        [
            _RG,
            "--with-filename",
            "--no-line-number",
            "--no-heading",
            "-o",
            r"ANCHOR:\s*[A-Z0-9_]+",
        ]
        + glob_args
        + [str(root)]
    )

    result = _run_text_command(cmd)
    # rg exit 1 = no matches (정상)
    if result is None or result.returncode not in (0, 1):
        return None
    index: dict[str, list[str]] = {}
    for line in (result.stdout or "").splitlines():
        if not line:
            continue
        # format: /abs/path/file.py:ANCHOR: FOO_START
        sep = line.index(":")
        filepath = line[:sep]
        match_text = line[sep + 1 :]
        m = _ANCHOR_RE.search(match_text)
        if not m:
            continue
        raw = m.group(1)
        base = re.sub(r"_(START|END)$", "", raw)
        try:
            rel = str(Path(filepath).relative_to(root))
        except ValueError:
            rel = filepath
        if rel not in index:
            index[rel] = []
        if base not in index[rel]:
            index[rel].append(base)
    return index


# === ANCHOR: FAST_TOOLS_END ===
