# === ANCHOR: PROTECTED_FILES_START ===
import os
import stat
from pathlib import Path

PROTECT_FILE = ".vibelign_protected"


def normalize_relpath(rel_path: str) -> str:
    return rel_path.replace("\\", "/")


# === ANCHOR: PROTECTED_FILES_GET_PROTECTED_START ===
def get_protected(root: Path) -> set[str]:
    """보호 목록 파일에서 보호된 경로 집합을 반환한다."""
    path = root / PROTECT_FILE
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        normalize_relpath(line.strip())
        for line in lines
        if line.strip() and not line.startswith("#")
    }


# === ANCHOR: PROTECTED_FILES_GET_PROTECTED_END ===


# === ANCHOR: PROTECTED_FILES_SAVE_PROTECTED_START ===
def save_protected(root: Path, protected: set[str]) -> None:
    """보호 목록을 파일에 저장한다."""
    path = root / PROTECT_FILE
    content = "# VibeLign 보호 파일 목록\n"
    content += "# vibelign protect 명령으로 관리하세요\n"
    for f in sorted(normalize_relpath(item) for item in protected):
        content += f"{f}\n"
    _ = path.write_text(content, encoding="utf-8")


# === ANCHOR: PROTECTED_FILES_SAVE_PROTECTED_END ===


# === ANCHOR: PROTECTED_FILES_IS_PROTECTED_START ===
def is_protected(rel_path: str, protected: set[str]) -> bool:
    """주어진 상대 경로가 보호 목록에 있는지 확인한다 (파일 또는 폴더 접두사 포함)."""
    if not protected:
        return False
    rel_path = normalize_relpath(rel_path)
    for pf in protected:
        pf_norm = normalize_relpath(pf)
        if rel_path == pf_norm:
            return True
        # 폴더 보호: 해당 폴더 하위 경로 전부 해당
        if rel_path.startswith(pf_norm.rstrip("/") + "/"):
            return True
    return False


# === ANCHOR: PROTECTED_FILES_IS_PROTECTED_END ===


# === ANCHOR: PROTECTED_FILES_SET_READONLY_START ===
def set_readonly(path: Path) -> None:
    """파일을 읽기 전용으로 설정한다 (Windows/Unix 공통)."""
    current = os.stat(path).st_mode
    os.chmod(path, current & ~(stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH))


def unset_readonly(path: Path) -> None:
    """파일의 읽기 전용을 해제하고 소유자 쓰기 권한을 복원한다."""
    current = os.stat(path).st_mode
    os.chmod(path, current | stat.S_IWRITE)
# === ANCHOR: PROTECTED_FILES_SET_READONLY_END ===


# === ANCHOR: PROTECTED_FILES_END ===
