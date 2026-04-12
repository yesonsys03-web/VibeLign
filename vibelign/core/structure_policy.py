# === ANCHOR: STRUCTURE_POLICY_START ===
from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from vibelign.core.meta_paths import MetaPaths
from vibelign.mcp.mcp_state_store import load_planning_session

COMMON_IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        "target",
        ".next",
        ".pnpm-store",
        ".idea",
        ".vscode",
        ".pytest_cache",
        ".mypy_cache",
        ".sisyphus",
        ".Trash",
        "Library",
        "CloudStorage",
    }
)

GENERATED_ARTIFACT_DIR_NAMES: frozenset[str] = frozenset(
    {"dist", "build", "target", ".next", ".pnpm-store", "node_modules"}
)

SOURCE_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".rs",
        ".go",
        ".java",
        ".cs",
        ".cpp",
        ".c",
        ".hpp",
        ".h",
    }
)

CORE_ENTRY_FILE_NAMES: frozenset[str] = frozenset(
    {
        "main.py",
        "app.py",
        "cli.py",
        "server.py",
        "index.js",
        "app.js",
        "main.js",
        "main.ts",
        "index.ts",
        "main.rs",
        "main.go",
        "main.cpp",
        "Program.cs",
        "vib_cli.py",
        "mcp_server.py",
    }
)

SCAN_EXTRA_IGNORED: frozenset[str] = frozenset(
    {"docs", "tests", ".github", ".vibelign"}
)
SCAN_IGNORED_DIRS: frozenset[str] = COMMON_IGNORED_DIRS | SCAN_EXTRA_IGNORED
SCAN_IGNORED_DIRS_LOWER: frozenset[str] = frozenset(
    name.lower() for name in SCAN_IGNORED_DIRS
)

CHECKPOINT_EXTRA_IGNORED: frozenset[str] = frozenset()
CHECKPOINT_IGNORED_DIRS: frozenset[str] = COMMON_IGNORED_DIRS | CHECKPOINT_EXTRA_IGNORED
CHECKPOINT_IGNORED_DIRS_LOWER: frozenset[str] = frozenset(
    name.lower() for name in CHECKPOINT_IGNORED_DIRS
)

TRANSFER_EXTRA_IGNORED: frozenset[str] = frozenset({".vibelign"})
TRANSFER_TREE_IGNORED_DIRS: frozenset[str] = (
    COMMON_IGNORED_DIRS | TRANSFER_EXTRA_IGNORED
)
TRANSFER_TREE_IGNORED_DIRS_LOWER: frozenset[str] = frozenset(
    name.lower() for name in TRANSFER_TREE_IGNORED_DIRS
)

CHECKPOINT_IGNORED_FILES: frozenset[str] = frozenset(
    {
        "VIBELIGN_PATCH_REQUEST.md",
        "VIBELIGN_EXPLAIN.md",
        "VIBELIGN_GUARD.md",
        "VIBELIGN_ASK.md",
        "anchor_meta.json",
        "project_map.json",
        "state.json",
        "watch_state.json",
        "watch.log",
        "scan_cache.json",
        "analysis_cache.json",
        "ui_label_index.json",
    }
)

HANDOFF_SKIP_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dylib",
        ".dll",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".ico",
        ".zip",
        ".tar",
        ".gz",
        ".lock",
        ".egg-info",
    }
)

HANDOFF_KEY_FILE_NAMES: frozenset[str] = frozenset(
    {
        "main.py",
        "app.py",
        "index.py",
        "server.py",
        "index.js",
        "app.js",
        "main.js",
        "index.ts",
        "app.ts",
        "main.ts",
        "main.go",
        "main.rs",
        "Main.java",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
    }
)

HANDOFF_SKIP_PREFIXES: tuple[str, ...] = (".vibelign", ".git", "__pycache__")

STRUCTURE_PATH_PREFIXES: tuple[str, ...] = (
    "vibelign/core/",
    "vibelign/commands/",
    "vibelign/mcp/",
    "vibelign/service/",
    "vibelign/patch/",
)

_DEFAULT_SMALL_FIX_THRESHOLD = 30

SOURCE_FILE_SUFFIXES: tuple[str, ...] = tuple(
    sorted(ext.lstrip(".") for ext in SOURCE_FILE_EXTENSIONS)
)


# === ANCHOR: STRUCTURE_POLICY_NORMALIZE_IGNORED_NAMES_START ===
def normalize_ignored_names(names: Iterable[str]) -> frozenset[str]:
    return frozenset(name.lower() for name in names)


# === ANCHOR: STRUCTURE_POLICY_NORMALIZE_IGNORED_NAMES_END ===


# === ANCHOR: STRUCTURE_POLICY_HAS_IGNORED_PART_START ===
def has_ignored_part(
    parts: tuple[str, ...],
    ignored: Iterable[str] = SCAN_IGNORED_DIRS_LOWER,
    # === ANCHOR: STRUCTURE_POLICY_HAS_IGNORED_PART_END ===
) -> bool:
    ignored_lower = (
        ignored if isinstance(ignored, frozenset) else normalize_ignored_names(ignored)
    )
    return any(part.lower() in ignored_lower for part in parts)


# === ANCHOR: STRUCTURE_POLICY_IS_SOURCE_FILE_START ===
def is_source_file(path: Path) -> bool:
    return path.suffix.lower() in SOURCE_FILE_EXTENSIONS


# === ANCHOR: STRUCTURE_POLICY_IS_SOURCE_FILE_END ===


# === ANCHOR: STRUCTURE_POLICY_IS_CORE_ENTRY_FILE_START ===
def is_core_entry_file(path: Path | str) -> bool:
    name = path if isinstance(path, str) else path.name
    return name in CORE_ENTRY_FILE_NAMES


# === ANCHOR: STRUCTURE_POLICY_IS_CORE_ENTRY_FILE_END ===


# === ANCHOR: STRUCTURE_POLICY_IS_GENERATED_ARTIFACT_PATH_START ===
def is_generated_artifact_path(path: Path | tuple[str, ...] | str) -> bool:
    if isinstance(path, Path):
        parts = path.parts
    elif isinstance(path, tuple):
        parts = path
    else:
        parts = tuple(path.replace("\\", "/").split("/"))
    return any(part.lower() in GENERATED_ARTIFACT_DIR_NAMES for part in parts)


# === ANCHOR: STRUCTURE_POLICY_IS_GENERATED_ARTIFACT_PATH_END ===


# === ANCHOR: STRUCTURE_POLICY_SHOULD_INCLUDE_VIBELIGN_FILE_START ===
def should_include_vibelign_file(filename: str) -> bool:
    return filename not in CHECKPOINT_IGNORED_FILES


# === ANCHOR: STRUCTURE_POLICY_SHOULD_INCLUDE_VIBELIGN_FILE_END ===


# === ANCHOR: STRUCTURE_POLICY_IS_TRIVIAL_PACKAGE_INIT_START ===
def is_trivial_package_init(path: Path, text: str) -> bool:
    if path.name != "__init__.py":
        return False

    stripped = text.strip()
    if not stripped:
        return True

    try:
        body = ast.parse(text).body
    except SyntaxError:
        return False

    for node in body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target_names: list[str] = []
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        target_names.append(target.id)
            elif isinstance(node.target, ast.Name):
                target_names.append(node.target.id)
            if target_names and all(name == "__all__" for name in target_names):
                continue
        return False
    return True


# === ANCHOR: STRUCTURE_POLICY_IS_TRIVIAL_PACKAGE_INIT_END ===


# === ANCHOR: STRUCTURE_POLICY_CLASSIFY_STRUCTURE_PATH_START ===
def classify_structure_path(rel_path: str) -> str:
    low = rel_path.lower()
    if low.startswith(".vibelign/"):
        return "meta"
    if low.startswith("docs/") or low.endswith(".md"):
        return "docs"
    if low.startswith("tests/") or "/tests/" in low or low.startswith("test_"):
        return "tests"
    if low in {"pyproject.toml", "package.json", "package-lock.json", "uv.lock"}:
        return "config"
    if (
        low.startswith(".claude/")
        or low.startswith(".github/")
        or low.endswith(".yaml")
        or low.endswith(".yml")
        or low.endswith(".toml")
    ):
        return "config"
    if low.startswith(STRUCTURE_PATH_PREFIXES):
        return "production"
    if low.endswith(".py"):
        return "non_vibelign_production"
    return "support"


# === ANCHOR: STRUCTURE_POLICY_CLASSIFY_STRUCTURE_PATH_END ===


# === ANCHOR: STRUCTURE_POLICY_IS_STRUCTURE_PRODUCTION_KIND_START ===
def is_structure_production_kind(path_kind: str) -> bool:
    return path_kind == "production"


# === ANCHOR: STRUCTURE_POLICY_IS_STRUCTURE_PRODUCTION_KIND_END ===


# === ANCHOR: STRUCTURE_POLICY_LOAD_ACTIVE_PLAN_PAYLOAD_START ===
def load_active_plan_payload(
    meta: MetaPaths,
) -> tuple[dict[str, object] | None, str | None, str | None]:
    planning = load_planning_session(meta)
    if not planning:
        return None, None, None
    if planning.get("override") is True:
        plan_id = planning.get("plan_id")
        return None, str(plan_id) if isinstance(plan_id, str) else None, "override"
    if planning.get("active") is not True:
        return None, None, None
    plan_id = planning.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        return None, None, "invalid_state"
    plan_path = meta.plans_dir / f"{plan_id}.json"
    if not plan_path.exists():
        return None, plan_id, "missing_plan_file"
    try:
        loaded = cast(object, json.loads(plan_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None, plan_id, "broken_plan"
    if not isinstance(loaded, dict):
        return None, plan_id, "broken_plan"
    payload = cast(dict[str, object], loaded)
    required_keys = {
        "id",
        "schema_version",
        "allowed_modifications",
        "required_new_files",
        "forbidden",
        "messages",
        "evidence",
        "scope",
    }
    if not required_keys.issubset(payload.keys()):
        return None, plan_id, "broken_plan"
    allowed_modifications = payload.get("allowed_modifications")
    required_new_files = payload.get("required_new_files")
    forbidden = payload.get("forbidden")
    if not isinstance(allowed_modifications, list):
        return None, plan_id, "broken_plan"
    if not isinstance(required_new_files, list):
        return None, plan_id, "broken_plan"
    if not isinstance(forbidden, list):
        return None, plan_id, "broken_plan"
    for item in cast(list[object], allowed_modifications):
        if not isinstance(item, dict):
            return None, plan_id, "broken_plan"
    for item in cast(list[object], required_new_files):
        if not isinstance(item, dict):
            return None, plan_id, "broken_plan"
    for item in cast(list[object], forbidden):
        if not isinstance(item, dict):
            return None, plan_id, "broken_plan"
    return payload, plan_id, None


# === ANCHOR: STRUCTURE_POLICY_LOAD_ACTIVE_PLAN_PAYLOAD_END ===


# === ANCHOR: STRUCTURE_POLICY_SMALL_FIX_LINE_THRESHOLD_START ===
def small_fix_line_threshold(meta: MetaPaths) -> int:
    if not meta.config_path.exists():
        return _DEFAULT_SMALL_FIX_THRESHOLD
    try:
        content = meta.config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _DEFAULT_SMALL_FIX_THRESHOLD
    match = re.search(r"^small_fix_line_threshold:\s*(\d+)\s*$", content, re.MULTILINE)
    if not match:
        return _DEFAULT_SMALL_FIX_THRESHOLD
    return int(match.group(1))


# === ANCHOR: STRUCTURE_POLICY_SMALL_FIX_LINE_THRESHOLD_END ===
# === ANCHOR: STRUCTURE_POLICY_END ===
