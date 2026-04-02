# === ANCHOR: PROTECTED_FILES_START ===
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
    """주어진 상대 경로가 보호 목록에 있는지 확인한다."""
    if not protected:
        return False
    rel_path = normalize_relpath(rel_path)
    # 정확히 일치하거나 경로 끝부분이 일치하면 보호된 파일로 간주
    for pf in protected:
        pf_norm = normalize_relpath(pf)
        if (
            rel_path == pf_norm
            or rel_path.endswith(pf_norm)
            or pf_norm.endswith(rel_path)
        ):
            return True
    return False


# === ANCHOR: PROTECTED_FILES_IS_PROTECTED_END ===
# === ANCHOR: PROTECTED_FILES_END ===
