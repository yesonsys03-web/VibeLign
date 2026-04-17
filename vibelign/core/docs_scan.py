# === ANCHOR: DOCS_SCAN_START ===
"""DocsViewer 인덱스용 재귀 markdown 스캔 전담 모듈.

os.walk 의 `dirs[:]` in-place pruning 으로 IGNORED_DIRS 를 워크에서 완전히 제외한다.
rglob 는 트리 전체를 돌고 나서 필터링하므로 무거운 서브트리 (node_modules, target) 에서
수만 개 경로를 읽는 비용을 피하려고 walk 방식을 썼다.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable


# 스캔 단계에서 아예 내려가지 않을 디렉토리 이름들. 숨김 디렉토리는 이름 규칙(`.`)로 별도 제외.
IGNORED_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        "target",
        "dist",
        "build",
        "out",
        "coverage",
        ".next",
        ".nuxt",
        ".turbo",
        ".cache",
        ".venv",
        "venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".gradle",
        ".idea",
        ".vscode",
        ".DS_Store",
    }
)


# === ANCHOR: DOCS_SCAN__SHOULD_SKIP_DIR_START ===
def _should_skip_dir(name: str) -> bool:
    if not name:
        return True
    if name.startswith("."):
        return True
    return name in IGNORED_DIRS
# === ANCHOR: DOCS_SCAN__SHOULD_SKIP_DIR_END ===


# === ANCHOR: DOCS_SCAN_ITER_MARKDOWN_FILES_START ===
def iter_markdown_files(
    root: Path, is_excluded: Callable[[Path], bool] | None = None
) -> list[Path]:
    """root 아래 모든 .md 파일을 재귀적으로 수집한다.

    - 숨김 디렉토리 (이름이 `.` 으로 시작) 와 IGNORED_DIRS 는 워크에서 pruned.
    - `is_excluded(resolved_path)` 가 True 를 주면 건너뛰어, 이미 명시 카테고리로 등록된
      파일이 "Docs" 라벨로 중복 등록되는 것을 호출자가 막을 수 있다.
    - 결과는 정렬되어 반환된다 (결정적 순서).
    """

    resolved_root = root.resolve()
    collected: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(resolved_root, followlinks=False):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        base = Path(dirpath)
        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            candidate = base / name
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if not resolved.is_file():
                continue
            if is_excluded is not None and is_excluded(resolved):
                continue
            collected.append(candidate)
    collected.sort(key=lambda p: p.as_posix())
    return collected
# === ANCHOR: DOCS_SCAN_ITER_MARKDOWN_FILES_END ===
# === ANCHOR: DOCS_SCAN_END ===
