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

from ..core import docs_cache as _DOCS_CACHE
from ..core import docs_index_cache as _DOCS_INDEX_CACHE
from ..core import docs_visualizer as _DOCS_VISUALIZER
from ..core import meta_paths as _META_PATHS

MetaPaths = _META_PATHS.MetaPaths
build_docs_index = _DOCS_CACHE.build_docs_index
visualize_markdown_file = _DOCS_VISUALIZER.visualize_markdown_file
write_docs_index_cache = _DOCS_INDEX_CACHE.write_docs_index_cache


# === ANCHOR: VIB_DOCS_BUILD_CMD_REBUILD_DOCS_INDEX_CACHE_START ===
def rebuild_docs_index_cache(root: Path) -> list[_DOCS_CACHE.DocsIndexEntry]:
    """docs index를 재계산하고 `.vibelign/docs_index.json` 에 캐시한 뒤 엔트리를 돌려준다.

    캐시 쓰기 실패는 치명적이지 않으므로 무시한다 (GUI는 subprocess 폴백으로 계속 동작).
    """

    resolved_root = root.resolve()
    entries = build_docs_index(resolved_root)
    try:
        write_docs_index_cache(MetaPaths(resolved_root), entries)
    except OSError as exc:
        print(f"docs index cache write skipped: {exc}", file=sys.stderr)
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


# === ANCHOR: VIB_DOCS_BUILD_CMD_RENDER_DOCS_VISUAL_ARTIFACTS_START ===
def render_docs_visual_artifacts(
    root: Path, relative_paths: Iterable[str]
# === ANCHOR: VIB_DOCS_BUILD_CMD_RENDER_DOCS_VISUAL_ARTIFACTS_END ===
) -> list[tuple[str, str]]:
    resolved_root = root.resolve()
    return [_artifact_json_for_path(resolved_root, path) for path in relative_paths]


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
        targets = [normalized]
    else:
        targets = sorted(entries.keys())

    rendered = render_docs_visual_artifacts(root, targets)

    meta.ensure_vibelign_dirs()
    if source_relative_path is None:
        tmp_dir = Path(
            tempfile.mkdtemp(prefix="docs_visual_", dir=str(meta.vibelign_dir))
        )
        try:
            for relative_path, content in rendered:
                target = tmp_dir / f"{relative_path}.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            if meta.docs_visual_dir.exists():
                shutil.rmtree(meta.docs_visual_dir)
            tmp_dir.replace(meta.docs_visual_dir)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
    else:
        relative_path, content = rendered[0]
        _atomic_write_text(meta.docs_visual_path(relative_path), content)

    return {
        "ok": True,
        "count": len(rendered),
        "written": [relative_path for relative_path, _ in rendered],
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
