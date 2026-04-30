# === ANCHOR: DOCS_CACHE_START ===
from __future__ import annotations

import argparse
import csv
import html
import json
import hashlib
import os
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
from . import docs_scan as _DOCS_SCAN
from . import doc_sources as _DOC_SOURCES
from . import meta_paths as _META_PATHS


DOCS_VISUAL_SCHEMA_VERSION = 2
DOCS_VISUAL_GENERATOR_VERSION = "heuristic-v2"
TEXT_DOC_EXTENSIONS: frozenset[str] = frozenset({".md", ".markdown", ".txt", ".csv"})


@dataclass(frozen=True)
# === ANCHOR: DOCS_CACHE_DOCSINDEXENTRY_START ===
class DocsIndexEntry:
    category: str
    path: str
    title: str
    modified_at_ms: int
    source_root: str | None = None
# === ANCHOR: DOCS_CACHE_DOCSINDEXENTRY_END ===


# === ANCHOR: DOCS_CACHE__NORMALIZE_PATH_START ===
def _normalize_path(path: Path) -> str:
    return path.as_posix()
# === ANCHOR: DOCS_CACHE__NORMALIZE_PATH_END ===


# === ANCHOR: DOCS_CACHE_NORMALIZE_DOC_TEXT_BYTES_START ===
def normalize_doc_text_bytes(raw: bytes) -> str:
    """Canonical text normalization for docs viewer source_hash.

    Ownership note: this module owns the canonical source_hash contract used by
    Python helpers and mirrored by the GUI/Tauri reader. The contract is:
    1) strip UTF-8 BOM if present
    2) decode as UTF-8
    3) normalize line endings to LF
    4) hash normalized UTF-8 text with SHA-256
    """

    clean = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    text = clean.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n")
# === ANCHOR: DOCS_CACHE_NORMALIZE_DOC_TEXT_BYTES_END ===


def _decode_utf8_document(raw: bytes, label: str) -> str:
    try:
        return normalize_doc_text_bytes(raw)
    except UnicodeDecodeError as exc:
        raise ValueError(f"UTF-8 {label} 문서만 읽을 수 있어요") from exc


def _read_json_document(path: Path) -> str:
    text = _decode_utf8_document(path.read_bytes(), "JSON")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _read_csv_document(path: Path) -> str:
    text = _decode_utf8_document(path.read_bytes(), "CSV")
    rows = list(csv.reader(StringIO(text)))
    if not rows:
        return text
    widths = [
        max(len(row[index]) if index < len(row) else 0 for row in rows)
        for index in range(max(len(row) for row in rows))
    ]
    rendered: list[str] = []
    for row in rows:
        rendered.append(
            " | ".join(
                (row[index] if index < len(row) else "").ljust(widths[index])
                for index in range(len(widths))
            ).rstrip()
        )
    return "\n".join(rendered) + "\n"


def _xml_text_from_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("word/document.xml")
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        raise ValueError("DOCX 본문을 읽을 수 없어요") from exc
    xml = raw.decode("utf-8", errors="ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"</w:tr>", "\n", xml)
    xml = re.sub(r"</w:tc>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return html.unescape(text).replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def _printable_runs(raw: bytes) -> str:
    ascii_runs = re.findall(rb"[\x09\x0a\x0d\x20-\x7e]{4,}", raw)
    parts = [chunk.decode("utf-8", errors="ignore") for chunk in ascii_runs]
    try:
        utf16 = raw.decode("utf-16le", errors="ignore")
    except UnicodeError:
        utf16 = ""
    parts.extend(re.findall(r"[\w\s가-힣.,;:!?()\[\]{}\-/]{8,}", utf16))
    cleaned = [part.strip() for part in parts if part.strip()]
    return "\n".join(cleaned[:400]) + ("\n" if cleaned else "")


def _read_pdf_document(path: Path) -> str:
    text = _printable_runs(path.read_bytes())
    if text:
        return text
    raise ValueError("PDF 텍스트를 추출할 수 없어요")


def _read_doc_document(path: Path) -> str:
    text = _printable_runs(path.read_bytes())
    if text:
        return text
    raise ValueError("DOC 텍스트를 추출할 수 없어요")


def read_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _read_json_document(path)
    if suffix == ".csv":
        return _read_csv_document(path)
    if suffix == ".docx":
        return _xml_text_from_docx(path)
    if suffix == ".pdf":
        return _read_pdf_document(path)
    if suffix == ".doc":
        return _read_doc_document(path)
    if suffix in TEXT_DOC_EXTENSIONS:
        return _decode_utf8_document(path.read_bytes(), "텍스트")
    raise ValueError(f"지원하지 않는 문서 형식입니다: {suffix or path.name}")


# === ANCHOR: DOCS_CACHE_COMPUTE_SOURCE_HASH_FROM_TEXT_START ===
def compute_source_hash_from_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
# === ANCHOR: DOCS_CACHE_COMPUTE_SOURCE_HASH_FROM_TEXT_END ===


# === ANCHOR: DOCS_CACHE_COMPUTE_SOURCE_HASH_START ===
def compute_source_hash(path: Path) -> str:
    return compute_source_hash_from_text(read_document_text(path))
# === ANCHOR: DOCS_CACHE_COMPUTE_SOURCE_HASH_END ===


# === ANCHOR: DOCS_CACHE__READ_TITLE_START ===
def _read_title(path: Path) -> str:
    try:
        if path.suffix.lower() in TEXT_DOC_EXTENSIONS | {".json", ".csv"}:
            text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        else:
            text = read_document_text(path)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or path.stem
            if stripped:
                return stripped[:80]
    except OSError as exc:
        print(f"[WARN] docs title fallback for {path}: {exc}", file=sys.stderr)
    except ValueError as exc:
        print(f"[WARN] docs title fallback for {path}: {exc}", file=sys.stderr)
    return path.stem.replace("-", " ").replace("_", " ").strip() or path.name
# === ANCHOR: DOCS_CACHE__READ_TITLE_END ===


def _iter_supported_doc_files(directory: Path, pattern: str) -> list[Path]:
    return sorted(
        path for path in directory.glob(pattern)
        if _DOCS_SCAN.is_supported_doc_file(path.name)
    )


# === ANCHOR: DOCS_CACHE__ITER_INDEX_TARGETS_START ===
def _iter_index_targets(root: Path) -> tuple[list[tuple[str, Path, str | None]], list[str]]:
    targets: list[tuple[str, Path, str | None]] = []
    seen: set[Path] = set()
    warnings: list[str] = []

    # === ANCHOR: DOCS_CACHE_ADD_START ===
    def add(category: str, path: Path, source_root: str | None = None) -> None:
        if not path.is_file():
            return
        try:
            resolved = path.resolve()
        except OSError:
            return
        if resolved in seen:
            return
        seen.add(resolved)
        targets.append((category, path, source_root))

    # VibeLign 전용 카테고리 — 알려진 경로를 먼저 등록해 카테고리 라벨을 보존한다.
    # === ANCHOR: DOCS_CACHE_ADD_END ===
    add("Context", root / "PROJECT_CONTEXT.md")

    # 일반 프로젝트도 흔히 두는 README — case-insensitive FS에서 중복 방지를 위해 첫 매치만.
    for name in (
        "README.md",
        "Readme.md",
        "readme.md",
        "README.markdown",
        "README.txt",
        "readme.txt",
    ):
        candidate = root / name
        if candidate.is_file():
            add("Readme", candidate)
            break

    add("Manual", root / "docs" / "MANUAL.md")

    wiki_dir = root / "docs" / "wiki"
    if wiki_dir.is_dir():
        for path in _iter_supported_doc_files(wiki_dir, "**/*"):
            add("Wiki", path)

    specs_dir = root / "docs" / "superpowers" / "specs"
    if specs_dir.is_dir():
        for path in _iter_supported_doc_files(specs_dir, "*"):
            add("Spec", path)

    plans_dir = root / "docs" / "superpowers" / "plans"
    if plans_dir.is_dir():
        for path in _iter_supported_doc_files(plans_dir, "*"):
            add("Plan", path)

    # 일반 사용자 프로젝트 지원 — 루트 직속 문서 파일 (README 외)
    for path in _iter_supported_doc_files(root, "*"):
        add("Root", path)

    # docs/ 하위 모든 문서 파일 (위 카테고리에 속하지 않은 것만 "Docs"로 잡힘)
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        for path in _iter_supported_doc_files(docs_dir, "**/*"):
            add("Docs", path)

    # 등록된 extra sources — allowlist 방식: 등록된 root만 직접 walk하고,
    # 등록 root 내 hidden sub-dir는 _should_skip_dir로 계속 prune한다.
    # built-in 패스가 먼저 실행됐으므로 seen에 이미 있는 파일은 자동으로 skip(built-in wins).
    # NOTE: iter_markdown_files catchall 보다 먼저 실행해야 Custom 라벨이 Docs로 덮이지 않는다.
    doc_sources_obj = _DOC_SOURCES.load(_META_PATHS.MetaPaths(root))
    for source_rel in doc_sources_obj.sources:
        extra_root = root / source_rel
        if not extra_root.is_dir():
            warnings.append(
                f"extra source '{source_rel}': 경로가 없거나 디렉터리가 아니어서 건너뜁니다."
            )
            continue

        count = 0
        cap = _DOC_SOURCES.MAX_FILES_PER_SOURCE
        capped = False
        for dirpath, dirnames, filenames in os.walk(str(extra_root), followlinks=False):
            # 등록된 source root 자체의 이름은 필터하지 않음 (allowlist 의도).
            # subdirectory만 _should_skip_dir로 prune.
            dirnames[:] = [d for d in dirnames if not _DOCS_SCAN._should_skip_dir(d)]
            base = Path(dirpath)
            for name in sorted(filenames):
                if not _DOCS_SCAN.is_supported_doc_file(name):
                    continue
                if count >= cap:
                    capped = True
                    break
                candidate = base / name
                try:
                    resolved = candidate.resolve()
                except OSError:
                    continue
                if not resolved.is_file():
                    continue
                if resolved in seen:
                    continue
                count += 1
                add("Custom", candidate, source_rel)
            if capped:
                break

        if capped:
            warnings.append(
                f"extra source '{source_rel}': MAX_FILES_PER_SOURCE ({cap}) 초과 — "
                f"처음 {cap}개 파일만 인덱싱됩니다."
            )

    # 프로젝트 전체 재귀 스캔 — 사용자가 임의로 만든 문서 폴더(예: VibeLign_dev_plan/) 도
    # 사이드바에 노출한다. IGNORED_DIRS + 숨김 디렉토리는 docs_scan 에서 프루닝된다.
    for path in _DOCS_SCAN.iter_markdown_files(root, is_excluded=lambda p: p in seen):
        add("Docs", path)

    return targets, warnings
# === ANCHOR: DOCS_CACHE__ITER_INDEX_TARGETS_END ===


# === ANCHOR: DOCS_CACHE_BUILD_DOCS_INDEX_START ===
def build_docs_index_with_warnings(root: Path) -> tuple[list[DocsIndexEntry], list[str]]:
    resolved_root = root.resolve()
    entries: list[DocsIndexEntry] = []

    targets, warnings = _iter_index_targets(resolved_root)
    for category, path, source_root in targets:
        resolved = path.resolve()
        rel = _normalize_path(resolved.relative_to(resolved_root))
        stat = resolved.stat()
        entries.append(
            DocsIndexEntry(
                category=category,
                path=rel,
                title=_read_title(resolved),
                modified_at_ms=int(stat.st_mtime * 1000),
                source_root=source_root,
            )
        )

    entries.sort(key=lambda item: (-item.modified_at_ms, item.path))
    return entries, warnings


def build_docs_index(root: Path) -> list[DocsIndexEntry]:
    return build_docs_index_with_warnings(root)[0]
# === ANCHOR: DOCS_CACHE_BUILD_DOCS_INDEX_END ===


# === ANCHOR: DOCS_CACHE_DOCS_VISUAL_CONTRACT_START ===
def docs_visual_contract() -> dict[str, object]:
    return {
        "owner_module": "vibelign.core.docs_cache",
        "owner_function": "compute_source_hash",
        "schema_version": DOCS_VISUAL_SCHEMA_VERSION,
        "generator_version": DOCS_VISUAL_GENERATOR_VERSION,
        "minimum_required_fields": [
            "source_path",
            "source_hash",
            "generated_at",
            "generator_version",
            "schema_version",
        ],
        "invalid_when": [
            "schema_version_mismatch",
            "generator_version_mismatch",
            "missing_required_fields",
            "corrupt_json",
        ],
        "hash_spec": {
            "strip_utf8_bom": True,
            "line_endings": "lf",
            "encoding": "utf-8",
            "algorithm": "sha256",
        },
    }
# === ANCHOR: DOCS_CACHE_DOCS_VISUAL_CONTRACT_END ===


# === ANCHOR: DOCS_CACHE_DOCS_VISUAL_SCHEMA_EXAMPLE_START ===
def docs_visual_schema_example() -> dict[str, object]:
    return {
        "schema_version": DOCS_VISUAL_SCHEMA_VERSION,
        "generator_version": DOCS_VISUAL_GENERATOR_VERSION,
        "generated_at": "2026-04-13T00:00:00Z",
        "source_path": "docs/wiki/index.md",
        "source_hash": "<sha256-of-normalized-source>",
        "title": "VibeLign Wiki",
        "summary": "Stable visual artifact contract example.",
        "sections": [
            {"id": "intro", "title": "Intro", "level": 1, "summary": "Top section."}
        ],
        "glossary": [],
        "action_items": [],
        "diagram_blocks": [
            {
                "id": "diagram-heuristic-1",
                "kind": "mermaid",
                "title": "Overview",
                "source": 'mindmap\n  root(("VibeLign Wiki"))\n    "Intro"',
                "provenance": "heuristic",
                "generator": "heading-mindmap-v1",
                "confidence": "high",
                "warnings": [],
            }
        ],
        "warnings": [],
        "heuristic_fields": {
            "tldr_one_liner": "샘플 문서의 한 줄 요약.",
            "key_rules": ["핵심 규칙 1", "핵심 규칙 2"],
            "success_criteria": ["성공 기준 1"],
            "edge_cases": ["예외 상황 1"],
            "components": ["파서 — AST 변환"],
            "provenance": "heuristic",
            "generator": DOCS_VISUAL_GENERATOR_VERSION,
            "generated_at": "2026-04-17T00:00:00Z",
        },
        "ai_fields": None,
    }
# === ANCHOR: DOCS_CACHE_DOCS_VISUAL_SCHEMA_EXAMPLE_END ===


# === ANCHOR: DOCS_CACHE__PARSE_ARGS_START ===
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build canonical docs index for GUI/Tauri consumers"
    )
    parser.add_argument("root", help="Project root to index")
    parser.add_argument(
        "--print-visual-contract",
        action="store_true",
        help="Print the docs visual artifact contract and example schema",
    )
    return parser.parse_args()
# === ANCHOR: DOCS_CACHE__PARSE_ARGS_END ===


# === ANCHOR: DOCS_CACHE_MAIN_START ===
def main() -> int:
    args = _parse_args()
    if args.print_visual_contract:
        print(
            json.dumps(
                {
                    "contract": docs_visual_contract(),
                    "example_artifact": docs_visual_schema_example(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    root = Path(args.root)
    payload = [asdict(item) for item in build_docs_index(root)]
    print(json.dumps(payload, ensure_ascii=False))
    return 0
# === ANCHOR: DOCS_CACHE_MAIN_END ===


if __name__ == "__main__":
    raise SystemExit(main())
# === ANCHOR: DOCS_CACHE_END ===
