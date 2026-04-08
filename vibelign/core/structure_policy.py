# === ANCHOR: STRUCTURE_POLICY_START ===
from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

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
# === ANCHOR: STRUCTURE_POLICY_END ===
