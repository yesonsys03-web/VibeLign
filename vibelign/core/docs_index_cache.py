# === ANCHOR: DOCS_INDEX_CACHE_START ===
"""DocsViewer 사이드바용 인덱스 캐시 파일 I/O 전담 모듈.

캐시는 `.vibelign/docs_index.json` 에 원자적으로 기록되며, Tauri 쪽에서 먼저 이 파일을
읽고 없거나 stale 하면 `vib docs-index` 서브프로세스로 폴백한다.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from . import doc_sources as _DOC_SOURCES
from . import docs_cache as _DOCS_CACHE
from . import meta_paths as _META_PATHS


DocsIndexEntry = _DOCS_CACHE.DocsIndexEntry
MetaPaths = _META_PATHS.MetaPaths


DOCS_INDEX_CACHE_SCHEMA_VERSION = 2


# === ANCHOR: DOCS_INDEX_CACHE_PAYLOAD_START ===
def _make_payload(
    root: Path,
    entries: Iterable[DocsIndexEntry],
    *,
    extra_source_roots: list[str],
    sources_fingerprint: str,
) -> dict[str, object]:
    return {
        "schema_version": DOCS_INDEX_CACHE_SCHEMA_VERSION,
        "root": str(root.resolve()),
        "generated_at_ms": int(time.time() * 1000),
        "sources_fingerprint": sources_fingerprint,
        "allowlist": {"extra_source_roots": extra_source_roots},
        "entries": [asdict(entry) for entry in entries],
    }
# === ANCHOR: DOCS_INDEX_CACHE_PAYLOAD_END ===


# === ANCHOR: DOCS_INDEX_CACHE_WRITE_START ===
def write_docs_index_cache(
    meta: MetaPaths,
    entries: Iterable[DocsIndexEntry],
    *,
    extra_source_roots: list[str],
    sources_fingerprint: str,
) -> Path:
    """docs index 캐시를 원자적으로 기록한다.

    동일 FS 상의 NamedTemporaryFile 로 생성 후 os.replace 로 교체한다.
    Windows에서 replace 가 간헐적으로 실패하면 한 번 재시도한다.
    """

    meta.ensure_vibelign_dir()
    target = meta.docs_index_path
    payload = _make_payload(
        meta.root,
        entries,
        extra_source_roots=extra_source_roots,
        sources_fingerprint=sources_fingerprint,
    )
    serialized = json.dumps(payload, ensure_ascii=False)

    fd, tmp_name = tempfile.mkstemp(
        prefix=".docs_index.", suffix=".tmp", dir=str(meta.vibelign_dir)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(tmp_path, target)
        except OSError:
            if sys.platform == "win32":
                time.sleep(0.05)
                os.replace(tmp_path, target)
            else:
                raise
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise

    return target
# === ANCHOR: DOCS_INDEX_CACHE_WRITE_END ===


# === ANCHOR: DOCS_INDEX_CACHE_READ_START ===
def read_docs_index_cache(meta: MetaPaths) -> list[DocsIndexEntry] | None:
    """캐시를 읽어 엔트리 리스트를 돌려준다. miss/stale/corrupt 면 None."""

    target = meta.docs_index_path
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != DOCS_INDEX_CACHE_SCHEMA_VERSION:
        return None

    cached_root = payload.get("root")
    if not isinstance(cached_root, str):
        return None
    try:
        if Path(cached_root).resolve() != meta.root.resolve():
            return None
    except OSError:
        return None

    # Verify sources_fingerprint against current doc_sources
    cached_fingerprint = payload.get("sources_fingerprint")
    if not isinstance(cached_fingerprint, str):
        return None
    current_sources = _DOC_SOURCES.load(meta).sources
    current_fingerprint = _DOC_SOURCES.fingerprint(current_sources)
    if cached_fingerprint != current_fingerprint:
        return None

    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        return None

    result: list[DocsIndexEntry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            return None
        try:
            result.append(
                DocsIndexEntry(
                    category=str(item["category"]),
                    path=str(item["path"]),
                    title=str(item["title"]),
                    modified_at_ms=int(item["modified_at_ms"]),
                    source_root=item.get("source_root"),
                )
            )
        except (KeyError, TypeError, ValueError):
            return None
    return result
# === ANCHOR: DOCS_INDEX_CACHE_READ_END ===
# === ANCHOR: DOCS_INDEX_CACHE_END ===
