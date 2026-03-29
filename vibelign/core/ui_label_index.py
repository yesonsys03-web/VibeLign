# === ANCHOR: UI_LABEL_INDEX_START ===
"""UI에 노출되는 짧은 문자열 후보 인덱스 (순번 8 경량).

`.vibelign/ui_label_index.json`에 캐시. 없으면 `suggest_patch` 시 한 번 생성한다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_scan import iter_source_files, relpath_str

SCHEMA_VERSION = 1
# JSX 텍스트 노드: 대문자 시작(영문 UI 관례) 또는 한글 노출 문구
_JSX_TEXT = re.compile(r">([A-Z][A-Za-z0-9 _\-]{2,48})<")
_JSX_TEXT_KO = re.compile(r">([가-힣][가-힣0-9 _\-·…]{2,60})<")
# 정적 접근성·폼 속성 (동적 `{expr}` 제외)
_ATTR_UI_STRING = re.compile(
    r"(?:aria-label|data-testid|placeholder|title|alt)\s*=\s*"
    r'["\']([^"\'\\]{3,120})["\']',
    re.IGNORECASE,
)
_QUOTED_CAPS = re.compile(r'''["']([A-Z][A-Z0-9_]{2,24})["']''')


# === ANCHOR: UI_LABEL_INDEX__RECORD_START ===
def _record(
    acc: dict[str, list[dict[str, int | str]]],
    label: str,
    rel: str,
    line_no: int,
# === ANCHOR: UI_LABEL_INDEX__RECORD_END ===
) -> None:
    key = label.strip()
    if len(key) < 3:
        return
    entry = {"path": rel, "line": line_no}
    bucket = acc.setdefault(key, [])
    if len(bucket) >= 8:
        return
    if any(e["path"] == rel and e["line"] == line_no for e in bucket):
        return
    bucket.append(entry)


# === ANCHOR: UI_LABEL_INDEX_BUILD_UI_LABEL_INDEX_START ===
def build_ui_label_index(root: Path) -> dict[str, object]:
    entries: dict[str, list[dict[str, int | str]]] = {}
    for path in iter_source_files(root):
        if path.suffix.lower() not in {".tsx", ".jsx", ".vue"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = relpath_str(root, path)
        for i, line in enumerate(text.splitlines(), start=1):
            for m in _JSX_TEXT.finditer(line):
                _record(entries, m.group(1), rel, i)
            for m in _JSX_TEXT_KO.finditer(line):
                _record(entries, m.group(1), rel, i)
            for m in _ATTR_UI_STRING.finditer(line):
                _record(entries, m.group(1).strip(), rel, i)
            for m in _QUOTED_CAPS.finditer(line):
                _record(entries, m.group(1), rel, i)
    return {"schema_version": SCHEMA_VERSION, "labels": entries}
# === ANCHOR: UI_LABEL_INDEX_BUILD_UI_LABEL_INDEX_END ===


# === ANCHOR: UI_LABEL_INDEX_REFRESH_UI_LABEL_INDEX_START ===
def refresh_ui_label_index(root: Path) -> None:
    meta = MetaPaths(root)
    meta.ensure_vibelign_dir()
    payload = build_ui_label_index(root)
    meta.ui_label_index_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
# === ANCHOR: UI_LABEL_INDEX_REFRESH_UI_LABEL_INDEX_END ===


# === ANCHOR: UI_LABEL_INDEX_LOAD_UI_LABEL_INDEX_START ===
def load_ui_label_index(root: Path) -> dict[str, list[dict[str, int | str]]]:
    meta = MetaPaths(root)
    if not meta.ui_label_index_path.exists():
        try:
            refresh_ui_label_index(root)
        except OSError:
            return {}
    try:
        raw = json.loads(meta.ui_label_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    labels = raw.get("labels")
    if not isinstance(labels, dict):
        return {}
    out: dict[str, list[dict[str, int | str]]] = {}
    for k, v in labels.items():
        if not isinstance(k, str) or not isinstance(v, list):
            continue
        cleaned: list[dict[str, int | str]] = []
        for item in v:
            if not isinstance(item, dict):
                continue
            p = item.get("path")
            ln = item.get("line")
            if isinstance(p, str) and isinstance(ln, int):
                cleaned.append({"path": p, "line": ln})
        if cleaned:
            out[k] = cleaned
    return out
# === ANCHOR: UI_LABEL_INDEX_LOAD_UI_LABEL_INDEX_END ===


# === ANCHOR: UI_LABEL_INDEX_SCORE_BOOST_FOR_UI_LABELS_START ===
def score_boost_for_ui_labels(
    rel_path: str,
    request_tokens: list[str],
    index: dict[str, list[dict[str, int | str]]],
# === ANCHOR: UI_LABEL_INDEX_SCORE_BOOST_FOR_UI_LABELS_END ===
) -> tuple[int, list[str]]:
    """요청 토큰이 인덱스 라벨과 일치하고 해당 파일이 후보일 때 점수 가산."""
    if not index or not request_tokens:
        return 0, []
    boost = 0
    reasons: list[str] = []
    rel_norm = rel_path.replace("\\", "/")
    for label, hits in index.items():
        label_l = label.lower()
        for tok in request_tokens:
            if len(tok) < 3 and not (
                len(tok) == 2 and all("\uac00" <= c <= "\ud7a3" for c in tok)
            ):
                continue
            tmatch = (
                tok.upper() == label.upper()
                or tok.lower() in label_l
                or label_l in tok.lower()
            )
            if not tmatch:
                continue
            for h in hits:
                hp = str(h.get("path", "")).replace("\\", "/")
                if hp == rel_norm:
                    boost += 4
                    reasons.append(
                        f"UI 라벨 인덱스: 요청에 가까운 노출 문자열 «{label}»이 이 파일에 있음"
                    )
                    return boost, reasons[:2]
    return 0, []
# === ANCHOR: UI_LABEL_INDEX_END ===
