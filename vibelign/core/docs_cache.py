from __future__ import annotations

import argparse
import json
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DOCS_VISUAL_SCHEMA_VERSION = 1
DOCS_VISUAL_GENERATOR_VERSION = "phase5-schema"


@dataclass(frozen=True)
class DocsIndexEntry:
    category: str
    path: str
    title: str
    modified_at_ms: int


def _normalize_path(path: Path) -> str:
    return path.as_posix()


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


def compute_source_hash_from_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_source_hash(path: Path) -> str:
    return compute_source_hash_from_text(normalize_doc_text_bytes(path.read_bytes()))


def _read_title(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or path.stem
    except OSError:
        pass
    return path.stem.replace("-", " ").replace("_", " ").strip() or path.name


def _iter_index_targets(root: Path) -> list[tuple[str, Path]]:
    targets: list[tuple[str, Path]] = []

    project_context = root / "PROJECT_CONTEXT.md"
    if project_context.is_file():
        targets.append(("Context", project_context))

    manual = root / "docs" / "MANUAL.md"
    if manual.is_file():
        targets.append(("Manual", manual))

    for path in sorted((root / "docs" / "wiki").glob("**/*.md")):
        if path.is_file():
            targets.append(("Wiki", path))

    for path in sorted((root / "docs" / "superpowers" / "specs").glob("*.md")):
        if path.is_file():
            targets.append(("Spec", path))

    for path in sorted((root / "docs" / "superpowers" / "plans").glob("*.md")):
        if path.is_file():
            targets.append(("Plan", path))

    return targets


def build_docs_index(root: Path) -> list[DocsIndexEntry]:
    resolved_root = root.resolve()
    entries: list[DocsIndexEntry] = []

    for category, path in _iter_index_targets(resolved_root):
        resolved = path.resolve()
        rel = _normalize_path(resolved.relative_to(resolved_root))
        stat = resolved.stat()
        entries.append(
            DocsIndexEntry(
                category=category,
                path=rel,
                title=_read_title(resolved),
                modified_at_ms=int(stat.st_mtime * 1000),
            )
        )

    entries.sort(key=lambda item: (-item.modified_at_ms, item.path))
    return entries


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
        "diagram_blocks": [],
        "warnings": [],
    }


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


if __name__ == "__main__":
    raise SystemExit(main())
