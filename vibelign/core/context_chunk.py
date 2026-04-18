# === ANCHOR: CONTEXT_CHUNK_START ===
"""앵커 중심 컨텍스트 청크 (순번 6: 패딩 + 모듈 머리말 보강).

§6.1 확장 훅: 앵커가 파일 하단에 있어 윈도우가 상단을 건너뛸 때,
AST 없이도 import/export·전역 전처리 구간을 앞에 붙여 Generator 컨텍스트를 보강한다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from vibelign.core.anchor_tools import extract_anchor_line_ranges

DEFAULT_PAD_BEFORE = 10
DEFAULT_PAD_AFTER = 14
# 앵커가 위에서 멀 때 붙이는 모듈 머리말 최대 줄 수 (임포트·docstring·전역 등)
DEFAULT_PY_PREFIX_MAX_LINES = 52
DEFAULT_JS_TS_PREFIX_MAX_LINES = 52

_JS_TS_EXTENSIONS = frozenset({".ts", ".tsx", ".js", ".jsx"})

_TOP_LEVEL_DEF_PY = re.compile(r"^(async\s+)?(def|class)\s+\w")
# 첫 top-level function / class (export·default·async 허용, 익명 function( 도 허용)
_TOP_LEVEL_FN_OR_CLASS_TS = re.compile(
    r"^\s*(export\s+(default\s+)?)?(async\s+)?(function\s*(\(|[\w$])|class\s+[\w$])"
)


# === ANCHOR: CONTEXT_CHUNK__PYTHON_HEAD_EXCLUSIVE_END_START ===
def _python_head_exclusive_end(lines: list[str], *, max_scan: int) -> int:
    """첫 top-level def/class 직전 인덱스(0-based, exclusive 상한). 없으면 max_scan까지."""
    lim = min(len(lines), max_scan)
    text = "".join(lines)
    try:
        module = ast.parse(text)
    except SyntaxError:
        for i in range(lim):
            if _TOP_LEVEL_DEF_PY.match(lines[i]):
                return i
        return lim

    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return min(max(node.lineno - 1, 0), lim)
    return lim


# === ANCHOR: CONTEXT_CHUNK__PYTHON_HEAD_EXCLUSIVE_END_END ===


# === ANCHOR: CONTEXT_CHUNK__PYTHON_PREFIX_LINES_BEFORE_START ===
def _python_prefix_lines_before(
    lines: list[str],
    window_start_idx: int,
    *,
    max_prefix: int,
    # === ANCHOR: CONTEXT_CHUNK__PYTHON_PREFIX_LINES_BEFORE_END ===
) -> list[str]:
    """윈도우 시작(window_start_idx) 앞 구간 중, 컨텍스트에 붙일 상단 줄들."""
    if window_start_idx <= 0:
        return []
    if window_start_idx <= max_prefix:
        return lines[0:window_start_idx]
    head_end = _python_head_exclusive_end(lines, max_scan=min(240, len(lines)))
    take = min(head_end, max_prefix, window_start_idx)
    if take < 1:
        return []
    return lines[0:take]


# === ANCHOR: CONTEXT_CHUNK__JS_TS_HEAD_EXCLUSIVE_END_START ===
def _js_ts_head_exclusive_end(lines: list[str], *, max_scan: int) -> int:
    """첫 top-level function/class 직전 인덱스(0-based). 없으면 max_scan까지."""
    lim = min(len(lines), max_scan)
    for i in range(lim):
        if _TOP_LEVEL_FN_OR_CLASS_TS.match(lines[i]):
            return i
    return lim


# === ANCHOR: CONTEXT_CHUNK__JS_TS_HEAD_EXCLUSIVE_END_END ===


# === ANCHOR: CONTEXT_CHUNK__JS_TS_PREFIX_LINES_BEFORE_START ===
def _js_ts_prefix_lines_before(
    lines: list[str],
    window_start_idx: int,
    *,
    max_prefix: int,
    # === ANCHOR: CONTEXT_CHUNK__JS_TS_PREFIX_LINES_BEFORE_END ===
) -> list[str]:
    if window_start_idx <= 0:
        return []
    if window_start_idx <= max_prefix:
        return lines[0:window_start_idx]
    head_end = _js_ts_head_exclusive_end(lines, max_scan=min(240, len(lines)))
    take = min(head_end, max_prefix, window_start_idx)
    if take < 1:
        return []
    return lines[0:take]


# === ANCHOR: CONTEXT_CHUNK_FETCH_ANCHOR_CONTEXT_WINDOW_START ===
def fetch_anchor_context_window(
    path: Path,
    anchor_name: str,
    *,
    pad_before: int = DEFAULT_PAD_BEFORE,
    pad_after: int = DEFAULT_PAD_AFTER,
    py_prefix_max_lines: int = DEFAULT_PY_PREFIX_MAX_LINES,
    js_ts_prefix_max_lines: int = DEFAULT_JS_TS_PREFIX_MAX_LINES,
    # === ANCHOR: CONTEXT_CHUNK_FETCH_ANCHOR_CONTEXT_WINDOW_END ===
) -> str | None:
    if (
        not path.is_file()
        or not anchor_name
        or anchor_name
        in {
            "[없음]",
            "[먼저 앵커를 추가하세요]",
        }
    ):
        return None
    ranges = extract_anchor_line_ranges(path)
    if anchor_name not in ranges:
        return None
    start, end = ranges[anchor_name]
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(
            keepends=True
        )
    except OSError:
        return None
    if start < 1 or end < start:
        return None
    i0 = max(0, start - 1 - pad_before)
    i1 = min(len(lines), end + pad_after)
    body = "".join(lines[i0:i1]).strip()
    if not body:
        return None
    suf = path.suffix.lower()
    if suf == ".py" and i0 > 0 and py_prefix_max_lines > 0:
        prefix_lines = _python_prefix_lines_before(
            lines, i0, max_prefix=py_prefix_max_lines
        )
        if prefix_lines:
            prefix = "".join(prefix_lines).rstrip()
            sep = "\n\n# --- vibelign: module preamble (imports / globals above anchor window) ---\n\n"
            return (prefix + sep + body).strip()
    if suf in _JS_TS_EXTENSIONS and i0 > 0 and js_ts_prefix_max_lines > 0:
        prefix_lines = _js_ts_prefix_lines_before(
            lines, i0, max_prefix=js_ts_prefix_max_lines
        )
        if prefix_lines:
            prefix = "".join(prefix_lines).rstrip()
            sep = (
                "\n\n// --- vibelign: module preamble "
                "(imports / exports above anchor window) ---\n\n"
            )
            return (prefix + sep + body).strip()
    return body


# === ANCHOR: CONTEXT_CHUNK_END ===
