from pathlib import Path
import re
from vibeguard.core.project_scan import iter_source_files, safe_read_text

COMMENT_PREFIX = {
    ".py": "#", ".js": "//", ".ts": "//", ".jsx": "//", ".tsx": "//",
    ".java": "//", ".go": "//", ".rs": "//", ".c": "//", ".cpp": "//",
    ".h": "//", ".hpp": "//", ".cs": "//",
}
ANCHOR_RE = re.compile(r"ANCHOR:\s*([A-Z0-9_]+)")

def build_anchor_name(path: Path) -> str:
    return path.stem.upper().replace("-", "_").replace(" ", "_")

def build_anchor_block(path: Path):
    prefix = COMMENT_PREFIX.get(path.suffix.lower(), "#")
    name = build_anchor_name(path)
    return f"{prefix} === ANCHOR: {name}_START ===", f"{prefix} === ANCHOR: {name}_END ==="

def preview_anchor_targets(root: Path, allowed_exts=None):
    targets = []
    for path in iter_source_files(root):
        if allowed_exts is not None and path.suffix.lower() not in allowed_exts:
            continue
        text = safe_read_text(path)
        if text and "ANCHOR:" not in text:
            targets.append(path)
    return targets

def insert_module_anchors(path: Path) -> bool:
    text = safe_read_text(path)
    if not text or "ANCHOR:" in text:
        return False
    start, end = build_anchor_block(path)
    try:
        path.write_text(f"{start}\n{text.rstrip()}\n{end}\n", encoding="utf-8")
    except OSError as e:
        print(f"경고: {path}에 앵커를 쓸 수 없습니다: {e}")
        return False
    return True

def extract_anchors(path: Path) -> list[str]:
    return list(dict.fromkeys(m.group(1) for m in ANCHOR_RE.finditer(safe_read_text(path))))
