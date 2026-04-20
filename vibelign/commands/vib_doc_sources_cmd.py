# === ANCHOR: VIB_DOC_SOURCES_CMD_START ===
from __future__ import annotations
import argparse, json, sys
from dataclasses import asdict
from pathlib import Path
from ..core import doc_sources as _DOC_SOURCES
from ..core import meta_paths as _META_PATHS
from . import vib_docs_build_cmd as _DOCS_BUILD

def _resolve_root() -> Path:
    return _DOCS_BUILD._resolve_root()

def _emit_ok(sources: list[str], entries, warnings: list[str]) -> None:
    payload = {
        "ok": True,
        "sources": sources,
        "entries": [asdict(e) for e in entries],
        "warnings": warnings,
    }
    print(json.dumps(payload, ensure_ascii=False))

def _emit_err(exc: Exception) -> None:
    payload = {"ok": False, "error": str(exc)}
    print(json.dumps(payload, ensure_ascii=False))

def run_vib_doc_sources_list(args: argparse.Namespace) -> None:
    root = _resolve_root()
    try:
        sources = _DOC_SOURCES.load(_META_PATHS.MetaPaths(root)).sources
        # Also return current index for UI consumption
        entries, warnings = _DOCS_BUILD.rebuild_docs_index_cache_with_warnings(root)
        _emit_ok(sources, entries, warnings)
    except Exception as exc:
        _emit_err(exc)
        raise SystemExit(1)

def run_vib_doc_sources_add(args: argparse.Namespace) -> None:
    root = _resolve_root()
    path_arg = getattr(args, "path", "")
    if not isinstance(path_arg, str) or not path_arg.strip():
        _emit_err(ValueError("경로가 필요합니다 (vib doc-sources add <path>)"))
        raise SystemExit(2)
    try:
        meta = _META_PATHS.MetaPaths(root)
        _DOC_SOURCES.add(meta, path_arg)
        entries, warnings = _DOCS_BUILD.rebuild_docs_index_cache_with_warnings(root)
        sources = _DOC_SOURCES.load(meta).sources
        _emit_ok(sources, entries, warnings)
    except Exception as exc:
        _emit_err(exc)
        raise SystemExit(1)

def run_vib_doc_sources_remove(args: argparse.Namespace) -> None:
    # Must delete .vibelign/docs_visual/_extra/<normalized_source>/ subtree BEFORE rebuild.
    # Path traversal guard: resolved path must remain inside meta.docs_visual_dir / "_extra" / ...
    import shutil
    root = _resolve_root()
    path_arg = getattr(args, "path", "")
    if not isinstance(path_arg, str) or not path_arg.strip():
        _emit_err(ValueError("경로가 필요합니다 (vib doc-sources remove <path>)"))
        raise SystemExit(2)
    try:
        meta = _META_PATHS.MetaPaths(root)
        # Remove first — this normalizes and validates.
        # We need the normalized value for artifact cleanup.
        # Strategy: call _DOC_SOURCES.remove, then delete _extra/<normalized> subtree
        # using the raw input normalized via replace/strip so it matches what doc_sources stored.
        lightly = path_arg.replace("\\", "/").strip().strip("/")
        _DOC_SOURCES.remove(meta, path_arg)

        # After successful remove, clean orphan artifacts.
        extra_root = meta.docs_visual_dir / "_extra"
        if extra_root.is_dir():
            candidate = (extra_root / lightly).resolve()
            extra_root_resolved = extra_root.resolve()
            # Ensure candidate stays under _extra/ (path traversal guard)
            try:
                candidate.relative_to(extra_root_resolved)
                if candidate.is_dir() and candidate != extra_root_resolved:
                    shutil.rmtree(candidate, ignore_errors=True)
            except ValueError:
                # candidate is outside _extra/ — don't touch
                pass

        entries, warnings = _DOCS_BUILD.rebuild_docs_index_cache_with_warnings(root)
        sources = _DOC_SOURCES.load(meta).sources
        _emit_ok(sources, entries, warnings)
    except Exception as exc:
        _emit_err(exc)
        raise SystemExit(1)
# === ANCHOR: VIB_DOC_SOURCES_CMD_END ===
