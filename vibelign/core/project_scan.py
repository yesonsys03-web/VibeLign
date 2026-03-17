# === ANCHOR: PROJECT_SCAN_START ===
from pathlib import Path

IGNORED = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".pnpm-store",
    ".idea",
    ".vscode",
    ".pytest_cache",
    "docs",
    "tests",
    ".github",
    ".vibelign",
    ".vibelign",
}
SOURCE_EXTS = {
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


def iter_project_files(root: Path):
    for path in root.rglob("*"):
        if any(part in IGNORED for part in path.parts):
            continue
        if path.is_file():
            yield path


def iter_source_files(root: Path):
    from vibelign.core.fast_tools import has_fd, find_source_files_fd
    if has_fd():
        files = find_source_files_fd(root)
        if files:
            yield from files
            return
    for path in iter_project_files(root):
        if path.suffix.lower() in SOURCE_EXTS:
            yield path


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def line_count(path: Path) -> int:
    return len(safe_read_text(path).splitlines())


def relpath_str(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


_ENTRY_NAMES = {"main.py", "app.py", "cli.py", "index.js", "main.ts"}
_UI_TOKENS = ["ui", "view", "views", "window", "dialog", "widget", "screen"]
_SERVICE_TOKENS = [
    "service", "services", "api", "client", "server",
    "worker", "job", "task", "queue", "auth", "data",
]
_CORE_TOKENS = ["core", "engine", "patch", "anchor", "guard"]


def classify_file(path: Path, rel: str) -> str:
    low = rel.lower()
    if path.name in _ENTRY_NAMES:
        return "entry"
    if any(t in low for t in _UI_TOKENS):
        return "ui"
    if any(t in low for t in _SERVICE_TOKENS):
        return "service"
    if any(t in low for t in _CORE_TOKENS):
        return "core"
    return "other"
# === ANCHOR: PROJECT_SCAN_END ===
