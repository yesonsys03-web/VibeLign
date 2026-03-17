# === ANCHOR: SCAN_CACHE_START ===
"""증분 스캔 + 캐시 전략.

파일별로 mtime + size를 캐시 키로 저장한다.
변경된 파일만 re-scan하고, 나머지는 캐시에서 읽는다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


SCAN_CACHE_SCHEMA = 1


def load_scan_cache(cache_path: Path) -> dict[str, Any]:
    if not cache_path.exists():
        return {}
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCAN_CACHE_SCHEMA:
            return {}
        entries = payload.get("entries", {})
        return entries if isinstance(entries, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_scan_cache(cache_path: Path, entries: dict[str, Any]) -> None:
    try:
        payload = {"schema_version": SCAN_CACHE_SCHEMA, "entries": entries}
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(cache_path)
    except OSError:
        pass


def _cache_valid(entry: dict[str, Any], path: Path) -> bool:
    try:
        st = os.stat(path)
        return (
            abs(st.st_mtime - entry.get("mtime", 0)) < 0.001
            and st.st_size == entry.get("size", -1)
        )
    except OSError:
        return False


def incremental_scan(
    root: Path,
    cache_path: Path,
    force: bool = False,
    invalidated: Optional[set[str]] = None,
) -> dict[str, Any]:
    """모든 소스 파일의 스캔 결과를 반환한다.

    - force=True: 캐시 무시, 전체 재스캔
    - invalidated: watch 이벤트로 변경된 파일 경로 집합 (즉시 재스캔)
    - 나머지 파일: mtime + size 비교 → 같으면 캐시, 다르면 재스캔

    반환: {rel_path: {mtime, size, anchors, category, line_count}}
    """
    from vibelign.core.project_scan import (
        classify_file,
        iter_source_files,
        line_count,
        relpath_str,
    )
    from vibelign.core.anchor_tools import extract_anchors

    cache = {} if force else load_scan_cache(cache_path)
    new_cache: dict[str, Any] = {}
    current_paths: set[str] = set()

    for path in iter_source_files(root):
        rel = relpath_str(root, path)
        current_paths.add(rel)
        entry = cache.get(rel)
        force_rescan = invalidated is not None and rel in invalidated

        if not force_rescan and entry and _cache_valid(entry, path):
            new_cache[rel] = entry
        else:
            try:
                st = os.stat(path)
                new_cache[rel] = {
                    "mtime": st.st_mtime,
                    "size": st.st_size,
                    "anchors": extract_anchors(path),
                    "category": classify_file(path, rel),
                    "line_count": line_count(path),
                }
            except OSError:
                pass

    # 삭제된 파일은 캐시에서 제거 (current_paths에 없는 항목)
    new_cache = {k: v for k, v in new_cache.items() if k in current_paths}

    save_scan_cache(cache_path, new_cache)
    return new_cache
# === ANCHOR: SCAN_CACHE_END ===
