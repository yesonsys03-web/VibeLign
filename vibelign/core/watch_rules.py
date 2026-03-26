from pathlib import Path
from typing import Optional, Set

ENTRY_FILES = {
    "main.py",
    "index.js",
    "app.js",
    "main.ts",
    "index.ts",
    "main.rs",
    "main.go",
    "main.cpp",
    "Program.cs",
}
CATCH_ALL = {
    "utils.py",
    "helpers.py",
    "misc.py",
    "all_utils.py",
    "utils.js",
    "helpers.js",
    "misc.js",
    "utils.ts",
    "helpers.ts",
    "misc.ts",
}
UI_HINTS = [
    "qwidget",
    "mainwindow",
    "react",
    "component",
    "render(",
    "button",
    "layout",
    "window",
    "dialog",
    "route",
    "router",
]
BIZ_HINTS = [
    "hashlib",
    "threading",
    "copy2(",
    "requests",
    "sqlite3",
    "fetch(",
    "axios",
    "express(",
    "flask(",
    "fastapi",
    "django",
    "subprocess",
    "os.walk",
    "shutil",
]


def classify_event(
    path: Path,
    text: str,
    old_lines: Optional[int],
    new_lines: int,
    strict: bool = False,
    protected_files: Optional[Set[str]] = None,
):
    name = path.name
    warnings = []
    entry_warn = 120 if strict else 200
    entry_high = 200 if strict else 300
    anchor_limit = 40 if strict else 80

    def add(level, message, why, action):
        warnings.append(
            {
                "level": level,
                "path": str(path),
                "message": message,
                "why": why,
                "action": action,
            }
        )

    low = text.lower()

    # 보호된 파일 체크 (최우선)
    if protected_files:
        from vibelign.core.protected_files import is_protected

        try:
            rel_str = str(path)
            if is_protected(rel_str, protected_files) or is_protected(
                name, protected_files
            ):
                add(
                    "HIGH",
                    f"[잠금] 보호된 파일 {name}이 수정되었습니다",
                    "이 파일은 'vib protect'로 보호 설정된 파일입니다. AI가 건드리면 안 되는 파일입니다.",
                    "AI 수정을 즉시 중단하고 변경사항을 확인하세요. 되돌리려면: vib undo",
                )
        except Exception:
            pass

    if old_lines is not None and new_lines > old_lines and name in ENTRY_FILES:
        if new_lines >= entry_high:
            add(
                "HIGH",
                f"{name} 파일이 {old_lines}줄에서 {new_lines}줄로 늘었습니다",
                "진입 파일은 작게 유지해야 하며 주요 로직이 들어오면 안 됩니다.",
                "로직을 src/core, src/services 또는 별도 모듈로 옮기세요.",
            )
        elif new_lines >= entry_warn:
            add(
                "WARN",
                f"{name} 파일이 {old_lines}줄에서 {new_lines}줄로 늘었습니다",
                "진입 파일이 점점 커지고 있습니다.",
                "시작 코드는 작게 유지하고 기능 로직은 밖으로 빼세요.",
            )

    if name in CATCH_ALL:
        add(
            "WARN",
            f"{name}은 모든 것을 담는 파일 패턴입니다",
            "이런 파일은 관련 없는 코드가 계속 쌓여 유지보수가 어려워집니다.",
            "hash_utils.py나 backup_worker.py처럼 역할이 명확한 이름으로 바꾸세요.",
        )

    if new_lines > anchor_limit and "=== ANCHOR:" not in text:
        add(
            "WARN",
            f"{name}에 앵커가 없습니다",
            "앵커 없는 큰 파일은 AI가 파일 전체를 다시 쓰도록 유도합니다.",
            "`vib anchor`를 실행하거나 직접 앵커를 추가하세요.",
        )

    if (
        any(h in low for h in UI_HINTS)
        and any(h in low for h in BIZ_HINTS)
        and new_lines > 100
    ):
        add(
            "HIGH",
            f"{name}에 UI와 비즈니스 로직이 혼재할 수 있습니다",
            "혼재된 파일은 유지보수가 어렵고 AI가 계속 키우는 경향이 있습니다.",
            "UI 코드와 서비스/처리 로직을 분리하세요.",
        )

    if name in ENTRY_FILES and any(h in low for h in BIZ_HINTS) and new_lines > 80:
        add(
            "HIGH",
            f"{name}에 비즈니스 로직이 섞여 있을 수 있습니다",
            "시작 파일에는 앱 초기화 코드만 있어야 합니다.",
            "AI 수정 전에 처리 로직을 별도 모듈로 옮기세요.",
        )
    return warnings
