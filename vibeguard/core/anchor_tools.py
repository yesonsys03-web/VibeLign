from pathlib import Path
import re
from vibeguard.core.project_scan import iter_source_files, safe_read_text

COMMENT_PREFIX = {
    ".py": "#",
    ".js": "//",
    ".ts": "//",
    ".jsx": "//",
    ".tsx": "//",
    ".java": "//",
    ".go": "//",
    ".rs": "//",
    ".c": "//",
    ".cpp": "//",
    ".h": "//",
    ".hpp": "//",
    ".cs": "//",
}
ANCHOR_RE = re.compile(r"ANCHOR:\s*([A-Z0-9_]+)")
PY_SYMBOL_RE = re.compile(
    r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE
)
JS_SYMBOL_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?(?:function|class)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
CONST_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(",
    re.MULTILINE,
)


def build_anchor_name(path: Path) -> str:
    return re.sub(
        r"[^A-Z0-9_]", "_", path.stem.upper().replace("-", "_").replace(" ", "_")
    )


def normalize_anchor_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9_]", "_", name.upper())


def build_symbol_anchor_name(path: Path, symbol_name: str) -> str:
    return f"{build_anchor_name(path)}_{normalize_anchor_name(symbol_name)}"


def build_anchor_block(path: Path):
    prefix = COMMENT_PREFIX.get(path.suffix.lower(), "#")
    name = build_anchor_name(path)
    return (
        f"{prefix} === ANCHOR: {name}_START ===",
        f"{prefix} === ANCHOR: {name}_END ===",
    )


def preview_anchor_targets(root: Path, allowed_exts=None):
    targets = []
    for path in iter_source_files(root):
        if allowed_exts is not None and path.suffix.lower() not in allowed_exts:
            continue
        text = safe_read_text(path)
        if text and "ANCHOR:" not in text:
            targets.append(path)
    return targets


def _python_symbol_blocks(text: str):
    lines = text.splitlines()
    blocks = []
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(
            r"^(\s*)(async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", line
        )
        if not match:
            continue
        indent = len(match.group(1))
        symbol_name = match.group(3)
        end_idx = len(lines) - 1
        for probe in range(idx + 1, len(lines)):
            probe_line = lines[probe]
            probe_stripped = probe_line.strip()
            if not probe_stripped:
                continue
            probe_indent = len(probe_line) - len(probe_line.lstrip())
            if probe_indent <= indent and not probe_line.lstrip().startswith("#"):
                end_idx = probe - 1
                break
        while end_idx > idx and not lines[end_idx].strip():
            end_idx -= 1
        blocks.append((idx, end_idx, symbol_name, match.group(1)))
    return blocks


def _js_symbol_blocks(text: str):
    lines = text.splitlines()
    blocks = []
    patterns = [
        re.compile(
            r"^(\s*)(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)"
        ),
        re.compile(r"^(\s*)(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(
            r"^(\s*)(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\("
        ),
    ]
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("//"):
            continue
        match = None
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                break
        if not match:
            continue
        symbol_name = match.group(2)
        indent = match.group(1)
        saw_open = "{" in line
        depth = line.count("{") - line.count("}")
        if saw_open and depth <= 0:
            blocks.append((idx, idx, symbol_name, indent))
            continue
        end_idx = idx
        for probe in range(idx + 1, len(lines)):
            probe_line = lines[probe]
            if not saw_open and "{" in probe_line:
                saw_open = True
            if saw_open:
                depth += probe_line.count("{") - probe_line.count("}")
            end_idx = probe
            if saw_open and depth <= 0:
                break
        if not saw_open:
            continue
        while end_idx > idx and not lines[end_idx].strip():
            end_idx -= 1
        blocks.append((idx, end_idx, symbol_name, indent))
    return blocks


def insert_python_symbol_anchors(path: Path) -> bool:
    if path.suffix.lower() != ".py":
        return False
    text = safe_read_text(path)
    if not text:
        return False
    lines = text.splitlines()
    blocks = _python_symbol_blocks(text)
    if not blocks:
        return False
    existing = set(extract_anchors(path))
    changed = False
    for start_idx, end_idx, symbol_name, indent in reversed(blocks):
        anchor_name = build_symbol_anchor_name(path, symbol_name)
        if anchor_name in existing:
            continue
        start_marker = f"{indent}# === ANCHOR: {anchor_name}_START ==="
        end_marker = f"{indent}# === ANCHOR: {anchor_name}_END ==="
        if start_idx > 0 and lines[start_idx - 1].strip() == start_marker.strip():
            continue
        insert_end_at = min(end_idx + 1, len(lines))
        lines.insert(insert_end_at, end_marker)
        lines.insert(start_idx, start_marker)
        changed = True
    if not changed:
        return False
    try:
        _ = path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    except OSError as e:
        print(f"경고: {path}에 심볼 앵커를 쓸 수 없습니다: {e}")
        return False
    return True


def insert_js_symbol_anchors(path: Path) -> bool:
    if path.suffix.lower() not in {".js", ".ts", ".jsx", ".tsx"}:
        return False
    text = safe_read_text(path)
    if not text:
        return False
    lines = text.splitlines()
    blocks = _js_symbol_blocks(text)
    if not blocks:
        return False
    existing = set(extract_anchors(path))
    changed = False
    for start_idx, end_idx, symbol_name, indent in reversed(blocks):
        anchor_name = build_symbol_anchor_name(path, symbol_name)
        if anchor_name in existing:
            continue
        start_marker = f"{indent}// === ANCHOR: {anchor_name}_START ==="
        end_marker = f"{indent}// === ANCHOR: {anchor_name}_END ==="
        if start_idx > 0 and lines[start_idx - 1].strip() == start_marker.strip():
            continue
        insert_end_at = min(end_idx + 1, len(lines))
        lines.insert(insert_end_at, end_marker)
        lines.insert(start_idx, start_marker)
        changed = True
    if not changed:
        return False
    try:
        _ = path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    except OSError as e:
        print(f"경고: {path}에 JS/TS 심볼 앵커를 쓸 수 없습니다: {e}")
        return False
    return True


def insert_module_anchors(path: Path) -> bool:
    text = safe_read_text(path)
    if not text:
        return False
    start, end = build_anchor_block(path)
    if start in text or end in text:
        return False
    if path.suffix.lower() == ".py":
        _ = insert_python_symbol_anchors(path)
        text = safe_read_text(path)
        if not text:
            return False
    elif path.suffix.lower() in {".js", ".ts", ".jsx", ".tsx"}:
        _ = insert_js_symbol_anchors(path)
        text = safe_read_text(path)
        if not text:
            return False
    try:
        lines = text.splitlines()
        prefix_lines = []
        body_lines = lines
        while body_lines and (
            body_lines[0].startswith("#!")
            or body_lines[0].startswith("# -*-")
            or body_lines[0].startswith("# coding:")
        ):
            prefix_lines.append(body_lines.pop(0))
        wrapped = []
        wrapped.extend(prefix_lines)
        if prefix_lines:
            wrapped.append("")
        wrapped.append(start)
        wrapped.extend(body_lines)
        wrapped.append(end)
        _ = path.write_text("\n".join(wrapped).rstrip() + "\n", encoding="utf-8")
    except OSError as e:
        print(f"경고: {path}에 앵커를 쓸 수 없습니다: {e}")
        return False
    return True


def extract_anchors(path: Path) -> list[str]:
    anchors = []
    for match in ANCHOR_RE.finditer(safe_read_text(path)):
        raw = match.group(1)
        base = re.sub(r"_(START|END)$", "", raw)
        anchors.append(base)
    return list(dict.fromkeys(anchors))


def suggest_anchor_names(path: Path) -> list[str]:
    text = safe_read_text(path)
    if not text:
        return []
    names = []
    suffix = path.suffix.lower()
    if suffix == ".py":
        names.extend(match.group(1) for match in PY_SYMBOL_RE.finditer(text))
    elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
        names.extend(match.group(1) for match in JS_SYMBOL_RE.finditer(text))
        names.extend(match.group(1) for match in CONST_FUNC_RE.finditer(text))
    normalized = [
        normalize_anchor_name(name)
        for name in names
        if name and not name.startswith("__")
    ]
    return list(dict.fromkeys(normalized[:24]))


def collect_anchor_index(root: Path, allowed_exts=None) -> dict[str, list[str]]:
    index = {}
    for path in iter_source_files(root):
        if allowed_exts is not None and path.suffix.lower() not in allowed_exts:
            continue
        anchors = extract_anchors(path)
        if anchors:
            index[str(path.relative_to(root))] = anchors
    return index


def collect_anchor_metadata(
    root: Path, allowed_exts=None
) -> dict[str, dict[str, list[str]]]:
    metadata = {}
    for path in iter_source_files(root):
        if allowed_exts is not None and path.suffix.lower() not in allowed_exts:
            continue
        anchors = extract_anchors(path)
        suggested = suggest_anchor_names(path)
        if anchors or suggested:
            metadata[str(path.relative_to(root))] = {
                "anchors": anchors,
                "suggested_anchors": suggested,
            }
    return metadata


def validate_anchor_file(path: Path) -> list[str]:
    text = safe_read_text(path)
    if not text:
        return ["파일 내용을 읽을 수 없습니다."]
    start_markers = re.findall(r"ANCHOR:\s*([A-Z0-9_]+)_START", text)
    end_markers = re.findall(r"ANCHOR:\s*([A-Z0-9_]+)_END", text)
    problems = []
    for name in start_markers:
        if name not in end_markers:
            problems.append(f"{name}_START 에 대응하는 END 가 없습니다")
    for name in end_markers:
        if name not in start_markers:
            problems.append(f"{name}_END 에 대응하는 START 가 없습니다")
    if not start_markers and not end_markers:
        problems.append("앵커가 없습니다")
    return problems
