from pathlib import Path

IGNORED = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build",
    ".next", ".pnpm-store", ".idea", ".vscode", ".pytest_cache",
    "docs", "tests", ".github"
}
SOURCE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".cs", ".cpp", ".c", ".hpp", ".h"
}

def iter_project_files(root: Path):
    for path in root.rglob("*"):
        if any(part in IGNORED for part in path.parts):
            continue
        if path.is_file():
            yield path

def iter_source_files(root: Path):
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
