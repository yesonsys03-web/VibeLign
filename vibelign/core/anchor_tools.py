from pathlib import Path
import json
import re
from typing import Any, Optional

from vibelign.core.project_map import ProjectMapSnapshot
from vibelign.core.project_scan import iter_source_files, line_count, safe_read_text


from vibelign.terminal_render import cli_print

print = cli_print

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


def anchor_recommendation_details(
    root: Path, path: Path, project_map: Optional[ProjectMapSnapshot] = None
) -> dict[str, object]:
    rel = str(path.relative_to(root))
    text = safe_read_text(path)
    symbol_suggestions = suggest_anchor_names(path)
    score = 0
    reasons: list[str] = []
    lines = line_count(path)

    if lines >= 300:
        score += 4
        reasons.append(f"파일이 커서({lines}줄) 안전 구역을 먼저 나누는 편이 좋아요")
    elif lines >= 120:
        score += 2
        reasons.append(f"파일이 어느 정도 커서({lines}줄) 앵커가 있으면 더 안전해요")

    if project_map is not None:
        if rel in project_map.entry_files:
            score += 4
            reasons.append(
                "프로젝트 시작점과 가까운 파일이라 먼저 보호하는 편이 좋아요"
            )
        if rel in project_map.ui_modules:
            score += 3
            reasons.append("UI 파일이라 AI가 자주 건드릴 가능성이 있어요")
        if rel in project_map.service_modules:
            score += 2
            reasons.append("서비스 역할 파일이라 변경 범위를 나누면 안전해요")
        if rel in project_map.core_modules:
            score += 2
            reasons.append("핵심 로직 파일이라 구역을 나눠두면 실수를 줄일 수 있어요")
        if rel in project_map.large_files and not any(
            "파일이 커서" in reason for reason in reasons
        ):
            score += 2
            reasons.append("Project Map 에서도 큰 파일로 표시된 항목이에요")

    if len(symbol_suggestions) >= 4:
        score += 3
        reasons.append("함수나 클래스가 여러 개라 자연스러운 구역을 나누기 좋아요")
    elif len(symbol_suggestions) >= 2:
        score += 1
        reasons.append("구조가 나뉘어 있어 심볼 기준 앵커를 만들기 좋아요")

    if text:
        if text.count("def ") + text.count("class ") >= 4:
            score += 1
        if text.count("function ") + text.count("class ") >= 4:
            score += 1

    if not reasons:
        reasons.append("앵커가 없어서 기본 추천 대상에 포함됐어요")

    return {
        "path": rel,
        "score": score,
        "reasons": reasons,
        "suggested_anchors": symbol_suggestions,
        "line_count": lines,
    }


def recommend_anchor_targets(
    root: Path,
    allowed_exts=None,
    project_map: Optional[ProjectMapSnapshot] = None,
) -> list[dict[str, Any]]:
    recommendations = []
    for path in preview_anchor_targets(root, allowed_exts=allowed_exts):
        recommendations.append(anchor_recommendation_details(root, path, project_map))
    recommendations.sort(
        key=lambda item: (
            -int(item["score"]),
            -int(item["line_count"]),
            str(item["path"]),
        )
    )
    return recommendations


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
        base = re.sub(r"_(START|END)$", "", raw).rstrip("_")
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
    if allowed_exts is None:
        from vibelign.core.fast_tools import has_rg, grep_anchors_rg
        if has_rg():
            result = grep_anchors_rg(root)
            if result is not None:
                return result
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


def load_anchor_meta(root: Path) -> dict[str, dict]:
    """anchor_meta.json 로드. 없으면 빈 딕셔너리 반환."""
    from vibelign.core.meta_paths import MetaPaths
    meta = MetaPaths(root)
    if not meta.anchor_meta_path.exists():
        return {}
    try:
        return json.loads(meta.anchor_meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_anchor_meta(root: Path, data: dict[str, dict]) -> None:
    """anchor_meta.json 저장."""
    from vibelign.core.meta_paths import MetaPaths
    meta = MetaPaths(root)
    meta.ensure_vibelign_dir()
    meta.anchor_meta_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def set_anchor_intent(
    root: Path,
    anchor_name: str,
    intent: str,
    connects: Optional[list[str]] = None,
    warning: Optional[str] = None,
) -> None:
    """특정 앵커에 의도(intent) 정보를 저장한다."""
    data = load_anchor_meta(root)
    entry: dict = data.get(anchor_name, {})
    entry["intent"] = intent
    if connects is not None:
        entry["connects"] = connects
    if warning is not None:
        entry["warning"] = warning
    data[anchor_name] = entry
    save_anchor_meta(root, data)


def get_anchor_intent(root: Path, anchor_name: str) -> dict:
    """특정 앵커의 의도 정보를 반환. 없으면 빈 딕셔너리."""
    return load_anchor_meta(root).get(anchor_name, {})


def extract_anchor_line_ranges(path: Path) -> dict[str, tuple[int, int]]:
    """각 앵커의 START~END 줄 번호 반환. {anchor_name: (start_line, end_line)} (1-based)"""
    text = safe_read_text(path)
    if not text:
        return {}
    ranges: dict[str, tuple[int, int]] = {}
    starts: dict[str, int] = {}
    for i, line in enumerate(text.splitlines(), start=1):
        m_start = re.search(r"ANCHOR:\s*([A-Z0-9_]+)_START", line)
        if m_start:
            name = re.sub(r"_(START|END)$", "", m_start.group(1)).rstrip("_")
            starts[name] = i
            continue
        m_end = re.search(r"ANCHOR:\s*([A-Z0-9_]+)_END", line)
        if m_end:
            name = re.sub(r"_(START|END)$", "", m_end.group(1)).rstrip("_")
            if name in starts:
                ranges[name] = (starts.pop(name), i)
    return ranges


def extract_anchor_blocks(path: Path) -> dict[str, str]:
    """각 앵커의 START~END 사이 코드를 추출. {anchor_name: code}"""
    text = safe_read_text(path)
    if not text:
        return {}
    blocks: dict[str, str] = {}
    current_anchor: Optional[str] = None
    current_lines: list[str] = []
    for line in text.splitlines():
        m_start = re.search(r"ANCHOR:\s*([A-Z0-9_]+)_START", line)
        if m_start:
            current_anchor = re.sub(r"_(START|END)$", "", m_start.group(1)).rstrip("_")
            current_lines = []
            continue
        m_end = re.search(r"ANCHOR:\s*([A-Z0-9_]+)_END", line)
        if m_end and current_anchor:
            blocks[current_anchor] = "\n".join(current_lines).strip()
            current_anchor = None
            current_lines = []
            continue
        if current_anchor is not None:
            current_lines.append(line)
    return blocks


def generate_anchor_intents_with_ai(root: Path, paths: list[Path]) -> int:
    """AI를 사용해 anchor intent를 자동 생성하고 저장. 반환: 등록된 intent 수"""
    from vibelign.core.ai_explain import generate_text_with_ai, has_ai_provider
    if not has_ai_provider():
        return 0
    existing = load_anchor_meta(root)
    all_blocks: dict[str, str] = {}
    for path in paths:
        for anchor, code in extract_anchor_blocks(path).items():
            if anchor not in existing:
                all_blocks[anchor] = code[:400]
    if not all_blocks:
        return 0
    anchor_list = list(all_blocks.keys())
    numbered = "\n\n".join(
        f"[{i + 1}] {name}\n{code}"
        for i, (name, code) in enumerate(all_blocks.items())
    )
    prompt = (
        "다음은 코드 파일의 각 구역(앵커)입니다.\n"
        "각 구역이 무슨 일을 하는지 한국어로 한 줄(10~20자)로 설명해주세요.\n"
        "반드시 아래 형식으로만 출력하세요. 다른 말은 하지 마세요.\n"
        "[번호] 설명\n\n"
        + numbered
    )
    text, _ = generate_text_with_ai(prompt, quiet=True)
    if not text:
        return 0
    parsed: dict[str, str] = {}
    parts = re.split(r"\[(\d+)\]", text)
    i = 1
    while i + 1 < len(parts):
        idx = int(parts[i]) - 1
        val = parts[i + 1].strip().splitlines()[0].strip()
        if 0 <= idx < len(anchor_list) and val:
            parsed[anchor_list[idx]] = val
        i += 2
    for anchor, intent in parsed.items():
        set_anchor_intent(root, anchor, intent)
    return len(parsed)


def strip_anchors(path: Path) -> bool:
    """파일에서 모든 앵커 줄을 제거한다. 변경이 있으면 True를 반환."""
    text = safe_read_text(path)
    if not text:
        return False
    lines = text.splitlines()
    cleaned = [line for line in lines if not re.search(r"===\s*ANCHOR:", line)]
    if len(cleaned) == len(lines):
        return False
    try:
        path.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")
    except OSError as e:
        print(f"경고: {path} 앵커 제거 실패: {e}")
        return False
    return True


def validate_anchor_file(path: Path) -> list[str]:
    text = safe_read_text(path)
    if not text:
        return ["파일 내용을 읽을 수 없습니다."]
    start_markers = re.findall(r"ANCHOR:\s*([A-Z0-9_]+)_START\s*===", text)
    end_markers = re.findall(r"ANCHOR:\s*([A-Z0-9_]+)_END\s*===", text)
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
