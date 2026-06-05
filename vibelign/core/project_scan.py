# === ANCHOR: PROJECT_SCAN_START ===
import re
import os
from collections.abc import Generator
from pathlib import Path
from typing import TypedDict, cast

from vibelign.core.checkpoint_engine.rust_engine import scan_project_with_rust

from vibelign.core.structure_policy import (
    has_ignored_part,
    is_core_entry_file,
    is_source_file,
)


class SourceFileRecord(TypedDict):
    path: Path
    category: str | None
    imports: list[str] | None


def iter_project_files(root: Path) -> Generator[Path, None, None]:
    for path in root.rglob("*"):
        if has_ignored_part(path.parts):
            continue
        try:
            is_file = path.is_file()
        except OSError:
            continue
        if is_file:
            yield path


def iter_source_files(root: Path) -> Generator[Path, None, None]:
    for record in iter_source_file_records(root):
        yield record["path"]


def iter_source_file_records(root: Path) -> Generator[SourceFileRecord, None, None]:
    if _rust_project_scan_enabled():
        rust_records = _source_file_records_from_rust_project_scan(root)
        if rust_records is not None:
            yield from rust_records
            return
    for path in _python_source_files(root):
        yield {"path": path, "category": None, "imports": None}


def _python_source_files(root: Path) -> Generator[Path, None, None]:
    from vibelign.core.fast_tools import has_fd, find_source_files_fd

    if has_fd():
        files = find_source_files_fd(root)
        if files:
            yield from files
            return
    for path in iter_project_files(root):
        if is_source_file(path):
            yield path


def _rust_project_scan_enabled() -> bool:
    return os.environ.get("VIBELIGN_PROJECT_SCAN_RUST", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def _source_file_records_from_rust_project_scan(root: Path) -> list[SourceFileRecord] | None:
    report, warning = scan_project_with_rust(root)
    if warning or report is None:
        return None
    files = report.get("files")
    if not isinstance(files, list):
        return None
    records: list[SourceFileRecord] = []
    for item in cast(list[object], files):
        if not isinstance(item, dict):
            continue
        raw_item = cast(dict[object, object], item)
        path = raw_item.get("path")
        if isinstance(path, str) and path:
            rel_parts = tuple(Path(path.replace("\\", "/")).parts)
            if has_ignored_part(rel_parts):
                continue
            category = raw_item.get("category")
            raw_imports = raw_item.get("imports")
            import_items = cast(list[object], raw_imports) if isinstance(raw_imports, list) else None
            imports = [value for value in import_items if isinstance(value, str)] if import_items is not None else None
            records.append(
                {
                    "path": root / path,
                    "category": category if isinstance(category, str) else None,
                    "imports": imports,
                }
            )
    return records


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def line_count(path: Path) -> int:
    return len(safe_read_text(path).splitlines())


def relpath_str(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


_UI_TOKENS = ["ui", "view", "views", "window", "dialog", "widget", "screen"]
_SERVICE_TOKENS = [
    "service",
    "services",
    "api",
    "client",
    "server",
    "worker",
    "job",
    "task",
    "queue",
    "auth",
    "data",
]
_CORE_TOKENS = ["core", "engine", "patch", "anchor", "guard"]


_PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([.\w]+)\s+import\b|import\s+([.\w]+))",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[^'"`;]+?\s+from\s+)?|require\s*\(\s*)['"]([^'"]+)['"]""",
)


def extract_imports(path: Path) -> list[str]:
    """파일에서 import 대상을 raw 문자열로 추출.

    - Python: `from X import ...`, `import X` → `X`
    - JS/TS: `import ... from "X"`, `import "X"`, `require("X")` → `X`
    반환은 중복 제거된 순서 보존 리스트.
    """
    suffix = path.suffix.lower()
    text = safe_read_text(path)
    if not text:
        return []
    seen: list[str] = []
    if suffix == ".py":
        for match in _PY_IMPORT_RE.finditer(text):
            mod = match.group(1) or match.group(2)
            if mod and mod not in seen:
                seen.append(mod)
    elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        for match in _JS_IMPORT_RE.finditer(text):
            mod = match.group(1)
            if mod and mod not in seen:
                seen.append(mod)
    return seen


def classify_file(path: Path, rel: str) -> str:
    if is_core_entry_file(path):
        return "entry"
    parts = rel.replace("\\", "/").split("/")
    dir_low = "/".join(parts[:-1]).lower()
    if dir_low:
        if any(t in dir_low for t in _CORE_TOKENS):
            return "core"
        if any(t in dir_low for t in _UI_TOKENS):
            return "ui"
        if any(t in dir_low for t in _SERVICE_TOKENS):
            return "service"
    low = rel.lower()
    if any(t in low for t in _UI_TOKENS):
        return "ui"
    if any(t in low for t in _SERVICE_TOKENS):
        return "service"
    if any(t in low for t in _CORE_TOKENS):
        return "core"
    return "other"


# === ANCHOR: PROJECT_SCAN_END ===
