# === ANCHOR: VIB_DOCS_BUILD_CMD_START ===
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..core import doc_sources as _DOC_SOURCES
from ..core import docs_access as _DOCS_ACCESS
from ..core import docs_cache as _DOCS_CACHE
from ..core import docs_html_visualizer as _DOCS_HTML_VISUALIZER
from ..core import docs_index_cache as _DOCS_INDEX_CACHE
from ..core import docs_visualizer as _DOCS_VISUALIZER
from ..core import meta_paths as _META_PATHS

MetaPaths = _META_PATHS.MetaPaths
build_docs_index = _DOCS_CACHE.build_docs_index
build_docs_index_with_warnings = _DOCS_CACHE.build_docs_index_with_warnings
visualize_markdown_file = _DOCS_VISUALIZER.visualize_markdown_file
write_docs_index_cache = _DOCS_INDEX_CACHE.write_docs_index_cache


# === ANCHOR: VIB_DOCS_BUILD_CMD_REBUILD_DOCS_INDEX_CACHE_START ===
def rebuild_docs_index_cache_with_warnings(
    root: Path,
) -> tuple[list[_DOCS_CACHE.DocsIndexEntry], list[str]]:
    """docs index를 재계산하고 `.vibelign/docs_index.json` 에 캐시한 뒤 (엔트리, 경고) 를 돌려준다.

    캐시 쓰기 실패는 치명적이지 않으므로 무시한다 (GUI는 subprocess 폴백으로 계속 동작).
    """
    resolved_root = root.resolve()
    meta = MetaPaths(resolved_root)
    entries, warnings = build_docs_index_with_warnings(resolved_root)
    doc_sources_obj = _DOC_SOURCES.load(meta)
    fp = _DOC_SOURCES.fingerprint(doc_sources_obj.sources)
    try:
        write_docs_index_cache(
            meta,
            entries,
            extra_source_roots=doc_sources_obj.sources,
            sources_fingerprint=fp,
        )
    except OSError as exc:
        print(f"docs index cache write skipped: {exc}", file=sys.stderr)
    return entries, warnings


def rebuild_docs_index_cache(root: Path) -> list[_DOCS_CACHE.DocsIndexEntry]:
    """docs index를 재계산하고 `.vibelign/docs_index.json` 에 캐시한 뒤 엔트리를 돌려준다."""
    entries, _warnings = rebuild_docs_index_cache_with_warnings(root)
    return entries
# === ANCHOR: VIB_DOCS_BUILD_CMD_REBUILD_DOCS_INDEX_CACHE_END ===


# === ANCHOR: VIB_DOCS_BUILD_CMD__FIND_PROJECT_ROOT_START ===
def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    home = Path.home().resolve()
    for candidate in (current, *current.parents):
        if candidate == home:
            break
        if (candidate / ".vibelign").exists():
            return candidate
    return current
# === ANCHOR: VIB_DOCS_BUILD_CMD__FIND_PROJECT_ROOT_END ===


# === ANCHOR: VIB_DOCS_BUILD_CMD__RESOLVE_ROOT_START ===
def _resolve_root() -> Path:
    env_root = os.environ.get("VIBELIGN_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return _find_project_root(Path.cwd())
# === ANCHOR: VIB_DOCS_BUILD_CMD__RESOLVE_ROOT_END ===


# === ANCHOR: VIB_DOCS_BUILD_CMD__ATOMIC_WRITE_TEXT_START ===
def _atomic_write_text(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    try:
        tmp.replace(target)
    except OSError:
        if sys.platform == "win32":
            time.sleep(0.05)
            tmp.replace(target)
        else:
            raise
# === ANCHOR: VIB_DOCS_BUILD_CMD__ATOMIC_WRITE_TEXT_END ===


def _replace_docs_visual_dir(target: Path, replacement: Path) -> None:
    last_error: OSError | None = None
    backup: Path | None = None
    for attempt in range(2):
        try:
            if target.exists():
                backup = target.with_name(
                    f"{target.name}.old-{os.getpid()}-{int(time.time() * 1000)}"
                )
                target.replace(backup)
            replacement.replace(target)
            if backup is not None:
                shutil.rmtree(backup, ignore_errors=True)
            return
        except OSError as exc:
            last_error = exc
            if backup is not None and backup.exists() and not target.exists():
                try:
                    backup.replace(target)
                except OSError:
                    pass
            if attempt == 0:
                time.sleep(0.05)
                continue
            break
    raise OSError(
        "docs visual cache directory를 교체할 수 없어요. "
        "다른 앱이 cache 파일을 열고 있다면 닫고 다시 시도하세요."
    ) from last_error


# === ANCHOR: VIB_DOCS_BUILD_CMD__ENTRY_MAP_START ===
def _entry_map(root: Path) -> dict[str, Any]:
    entries = rebuild_docs_index_cache(root)
    return {str(entry.path): entry for entry in entries}
# === ANCHOR: VIB_DOCS_BUILD_CMD__ENTRY_MAP_END ===


# === ANCHOR: VIB_DOCS_BUILD_CMD__ARTIFACT_JSON_FOR_PATH_START ===
def _artifact_json_for_path(root: Path, relative_path: str) -> tuple[str, str]:
    source_path = (root / relative_path).resolve()
    artifact = visualize_markdown_file(source_path)
    return relative_path, json.dumps(
        artifact.to_dict(), ensure_ascii=False, indent=2
    ) + "\n"
# === ANCHOR: VIB_DOCS_BUILD_CMD__ARTIFACT_JSON_FOR_PATH_END ===


def _html_artifact_json_for_path(root: Path, relative_path: str) -> tuple[str, str]:
    source_path = (root / relative_path).resolve()
    artifact = _DOCS_HTML_VISUALIZER.build_docs_html_artifact(source_path)
    return relative_path, json.dumps(
        artifact.to_dict(), ensure_ascii=False, indent=2
    ) + "\n"


# === ANCHOR: VIB_DOCS_BUILD_CMD_RENDER_DOCS_VISUAL_ARTIFACTS_START ===
def render_docs_visual_artifacts(
    root: Path, relative_paths: Iterable[str]
# === ANCHOR: VIB_DOCS_BUILD_CMD_RENDER_DOCS_VISUAL_ARTIFACTS_END ===
) -> list[tuple[str, str]]:
    resolved_root = root.resolve()
    return [_artifact_json_for_path(resolved_root, path) for path in relative_paths]


def render_docs_html_artifacts(
    root: Path, relative_paths: Iterable[str]
) -> list[tuple[str, str]]:
    resolved_root = root.resolve()
    return [_html_artifact_json_for_path(resolved_root, path) for path in relative_paths]


# === ANCHOR: VIB_DOCS_BUILD_CMD_BUILD_DOCS_VISUAL_CACHE_START ===
def build_docs_visual_cache(
    root: Path, source_relative_path: str | None = None
# === ANCHOR: VIB_DOCS_BUILD_CMD_BUILD_DOCS_VISUAL_CACHE_END ===
) -> dict[str, object]:
    root = root.resolve()
    meta = MetaPaths(root)
    entries = _entry_map(root)
    if not entries:
        return {"ok": True, "count": 0, "written": [], "root": str(root)}

    targets: list[str]
    if source_relative_path is not None:
        normalized = source_relative_path.replace("\\", "/")
        if normalized not in entries:
            raise ValueError(f"docs index에 없는 문서예요: {normalized}")
        if not _DOCS_ACCESS.is_canvas_eligible_path(normalized):
            raise ValueError(_DOCS_ACCESS.canvas_ineligible_reason(normalized))
        targets = [normalized]
    else:
        targets = sorted(
            path for path in entries.keys()
            if _DOCS_ACCESS.is_canvas_eligible_path(path)
        )

    rendered = render_docs_visual_artifacts(root, targets)
    html_rendered = render_docs_html_artifacts(root, targets)

    meta.ensure_vibelign_dirs()
    if source_relative_path is None:
        tmp_dir = Path(
            tempfile.mkdtemp(prefix="docs_visual_", dir=str(meta.vibelign_dir))
        )
        tmp_html_dir = Path(
            tempfile.mkdtemp(prefix="docs_html_", dir=str(meta.vibelign_dir))
        )
        try:
            for relative_path, content in rendered:
                is_extra = entries[relative_path].source_root is not None
                if is_extra:
                    target = tmp_dir / "_extra" / f"{relative_path}.json"
                else:
                    target = tmp_dir / f"{relative_path}.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            for relative_path, content in html_rendered:
                is_extra = entries[relative_path].source_root is not None
                if is_extra:
                    target = tmp_html_dir / "_extra" / f"{relative_path}.json"
                else:
                    target = tmp_html_dir / f"{relative_path}.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            _replace_docs_visual_dir(meta.docs_visual_dir, tmp_dir)
            _replace_docs_visual_dir(meta.docs_html_dir, tmp_html_dir)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            shutil.rmtree(tmp_html_dir, ignore_errors=True)
            raise
    else:
        relative_path, content = rendered[0]
        html_relative_path, html_content = html_rendered[0]
        is_extra = entries[normalized].source_root is not None
        _atomic_write_text(meta.docs_visual_path(relative_path, is_extra=is_extra), content)
        _atomic_write_text(meta.docs_html_path(html_relative_path, is_extra=is_extra), html_content)

    return {
        "ok": True,
        "count": len(rendered),
        "written": [relative_path for relative_path, _ in rendered],
        "html_written": [relative_path for relative_path, _ in html_rendered],
        "root": str(root),
    }


# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_BUILD_START ===
def run_vib_docs_build(args: argparse.Namespace) -> None:
    root = _resolve_root()
    target = getattr(args, "path", None)
    target_path = target if isinstance(target, str) and target.strip() else None
    try:
        result = build_docs_visual_cache(root, target_path)
    except Exception as exc:
        print(f"docs visual cache 생성 실패: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if target_path:
        print(f"docs visual cache 생성 완료: {target_path}")
    else:
        print(f"docs visual cache 전체 재생성 완료: {result['count']}개")
# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_BUILD_END ===


# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_ENHANCE_START ===
def run_vib_docs_enhance(args: argparse.Namespace) -> None:
    from ..core import docs_ai_enhance as _AI_ENHANCE

    root = _resolve_root()
    target = getattr(args, "path", None)
    if not isinstance(target, str) or not target.strip():
        print(
            "docs-enhance 는 문서 경로가 필요해요 (예: vib docs-enhance docs/wiki/index.md)",
            file=sys.stderr,
        )
        raise SystemExit(2)

    relative_path = target.replace("\\", "/")
    meta = MetaPaths(root)
    extra_sources = _DOC_SOURCES.load(meta).sources
    is_extra = any(
        relative_path == src or relative_path.startswith(f"{src}/")
        for src in extra_sources
    )
    artifact_path = meta.docs_visual_path(relative_path, is_extra=is_extra)
    if not artifact_path.exists():
        print(
            f"artifact 가 없어요. 먼저 vib docs-build '{relative_path}' 를 실행하세요.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    source_path = (root / relative_path).resolve()
    if not source_path.is_file():
        print(f"source markdown 이 없어요: {relative_path}", file=sys.stderr)
        raise SystemExit(3)

    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"source markdown 을 읽을 수 없어요: {exc}", file=sys.stderr)
        raise SystemExit(3) from exc

    try:
        result = _AI_ENHANCE.call_auto(source_text)
    except Exception as exc:
        print(f"AI 호출 실패: {exc}", file=sys.stderr)
        raise SystemExit(4) from exc

    existing = json.loads(artifact_path.read_text(encoding="utf-8"))
    source_hash = existing.get("source_hash", "")
    existing["ai_fields"] = {
        **result["fields"],
        "provenance": "ai_draft",
        "model": result["model"],
        "provider": result["provider"],
        "generated_at": _DOCS_VISUALIZER.current_generated_at(),
        "source_hash": source_hash,
        "tokens_input": result["tokens_input"],
        "tokens_output": result["tokens_output"],
        "cost_usd": result["cost_usd"],
    }
    _atomic_write_text(
        artifact_path, json.dumps(existing, ensure_ascii=False, indent=2) + "\n"
    )
    if getattr(args, "json", False):
        print(
            json.dumps(
                {"ok": True, "path": relative_path, "ai_fields": existing["ai_fields"]},
                ensure_ascii=False,
            )
        )
    else:
        print(
            f"AI 요약 완료: {relative_path} "
            f"(in={result['tokens_input']} out={result['tokens_output']} ${result['cost_usd']:.4f})"
        )
# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_ENHANCE_END ===


# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_INDEX_START ===
def run_vib_docs_index(args: argparse.Namespace) -> None:
    """GUI/Tauri 등 외부 호출자에게 docs index 또는 visual contract를 JSON으로 출력한다."""
    if getattr(args, "visual_contract", False):
        payload = {
            "contract": _DOCS_CACHE.docs_visual_contract(),
            "example_artifact": _DOCS_CACHE.docs_visual_schema_example(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if getattr(args, "html_contract", False):
        payload = {
            "contract": _DOCS_CACHE.docs_html_contract(),
            "example_artifact": _DOCS_CACHE.docs_html_schema_example(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    raw_path = getattr(args, "path", None)
    root = Path(raw_path).resolve() if raw_path else _resolve_root()
    try:
        entries = rebuild_docs_index_cache(root)
    except Exception as exc:
        print(f"docs index 생성 실패: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps([asdict(item) for item in entries], ensure_ascii=False))
# === ANCHOR: VIB_DOCS_BUILD_CMD_RUN_VIB_DOCS_INDEX_END ===
# === ANCHOR: VIB_DOCS_BUILD_CMD_END ===
