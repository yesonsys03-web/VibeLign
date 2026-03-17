# === ANCHOR: PROTECTED_FILES_START ===
from pathlib import Path

PROTECT_FILE = ".vibelign_protected"


# === ANCHOR: PROTECTED_FILES_GET_PROTECTED_START ===
def get_protected(root: Path) -> set:
    """보호 목록 파일에서 보호된 경로 집합을 반환한다."""
    path = root / PROTECT_FILE
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}
# === ANCHOR: PROTECTED_FILES_GET_PROTECTED_END ===


# === ANCHOR: PROTECTED_FILES_SAVE_PROTECTED_START ===
def save_protected(root: Path, protected: set) -> None:
    """보호 목록을 파일에 저장한다."""
    path = root / PROTECT_FILE
    content = "# VibeLign 보호 파일 목록\n"
    content += "# vibelign protect 명령으로 관리하세요\n"
    for f in sorted(protected):
        content += f"{f}\n"
    path.write_text(content, encoding="utf-8")
# === ANCHOR: PROTECTED_FILES_SAVE_PROTECTED_END ===


# === ANCHOR: PROTECTED_FILES_IS_PROTECTED_START ===
def is_protected(rel_path: str, protected: set) -> bool:
    """주어진 상대 경로가 보호 목록에 있는지 확인한다."""
    if not protected:
        return False
    # 정확히 일치하거나 경로 끝부분이 일치하면 보호된 파일로 간주
    for pf in protected:
        if rel_path == pf or rel_path.endswith(pf) or pf.endswith(rel_path):
            return True
    return False
# === ANCHOR: PROTECTED_FILES_IS_PROTECTED_END ===
# === ANCHOR: PROTECTED_FILES_END ===
