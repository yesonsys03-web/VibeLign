# === ANCHOR: IMPORT_RESOLVER_START ===
from __future__ import annotations

import re
from pathlib import Path

# JS/TS: import X from './path' | import { X } from "./path" | require('./path')
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w*{}\s,]+\s+from\s+)?|require\s*\(\s*)['"](\.[^'"]+)['"]""",
    re.MULTILINE,
)

# Python: from package.sub import X (absolute dotted)
_PY_FROM_RE = re.compile(
    r"^from\s+([\w.]+)\s+import",
    re.MULTILINE,
)

_JS_EXTS = (".tsx", ".ts", ".jsx", ".js")
_PY_EXT = ".py"


def _resolve_js_import(base_dir: Path, import_path: str, root: Path) -> Path | None:
    """'../Foo' → 실제 파일 경로 (프로젝트 내부만)."""
    candidate = (base_dir / import_path).resolve()
    checks: list[Path] = [candidate]
    if not candidate.suffix:
        for ext in _JS_EXTS:
            checks.append(candidate.with_suffix(ext))
        for idx in ("index.ts", "index.tsx", "index.js", "index.jsx"):
            checks.append(candidate / idx)
    for path in checks:
        if path.is_file():
            try:
                path.relative_to(root.resolve())
                return path
            except ValueError:
                pass
    return None


def _resolve_py_import(src_file: Path, module_str: str, root: Path) -> Path | None:
    """'vibelign.core.codespeak' → vibelign/core/codespeak.py (프로젝트 내부만)."""
    parts = module_str.split(".")
    candidate = root.joinpath(*parts).with_suffix(_PY_EXT)
    if candidate.is_file():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            pass
    pkg_root = src_file.parent
    candidate2 = pkg_root.joinpath(*parts).with_suffix(_PY_EXT)
    if candidate2.is_file():
        try:
            candidate2.relative_to(root)
            return candidate2
        except ValueError:
            pass
    return None


# === ANCHOR: IMPORT_RESOLVER_PARSE_LOCAL_IMPORTS_START ===
def parse_local_imports(file_path: Path, root: Path) -> list[Path]:
    """file_path 의 로컬(프로젝트 내) import 를 파싱해 실제 Path 목록을 반환한다.

    - JS/TS: 상대 경로 import ('.' 또는 '..' 시작)
    - Python: 절대 dotted import (프로젝트 루트 기준)
    단어장 없이 코드 구조만으로 의존 파일을 탐색한다.
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    results: list[Path] = []
    seen: set[Path] = set()
    ext = file_path.suffix.lower()

    if ext in _JS_EXTS:
        for m in _JS_IMPORT_RE.finditer(text):
            import_path = m.group(1)
            if not import_path.startswith("."):
                continue
            resolved = _resolve_js_import(file_path.parent, import_path, root.resolve())
            if resolved and resolved not in seen:
                seen.add(resolved)
                results.append(resolved)

    elif ext == _PY_EXT:
        for m in _PY_FROM_RE.finditer(text):
            module_str = m.group(1)
            if module_str.startswith("."):
                continue
            resolved = _resolve_py_import(file_path, module_str, root)
            if resolved and resolved not in seen:
                seen.add(resolved)
                results.append(resolved)

    return results
# === ANCHOR: IMPORT_RESOLVER_PARSE_LOCAL_IMPORTS_END ===
# === ANCHOR: IMPORT_RESOLVER_END ===
