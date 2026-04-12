# === ANCHOR: ANCHOR_TOOLS_START ===
from collections.abc import Collection
from pathlib import Path
import json
import re
from typing import TypeAlias, TypedDict, cast

from vibelign.core.project_map import ProjectMapSnapshot
from vibelign.core.project_scan import iter_source_files, line_count, safe_read_text


from vibelign.terminal_render import cli_print

print = cli_print

AllowedExts: TypeAlias = Collection[str]
SymbolBlock: TypeAlias = tuple[int, int, str, str]


class AnchorRecommendation(TypedDict):
    path: str
    score: int
    reasons: list[str]
    suggested_anchors: list[str]
    line_count: int


class AnchorMetadataEntry(TypedDict):
    anchors: list[str]
    suggested_anchors: list[str]


class AnchorMetaEntry(TypedDict, total=False):
    intent: str
    connects: list[str]
    warning: str
    aliases: list[str]
    description: str


def _normalize_object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    normalized: dict[str, object] = {}
    for key, item in raw.items():
        normalized[str(key)] = item
    return normalized


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    raw = cast(list[object], value)
    normalized: list[str] = []
    for item in raw:
        if isinstance(item, str):
            normalized.append(item)
    return normalized


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
ANCHOR_RE = re.compile(r"===\s*ANCHOR:\s*([A-Z0-9_]+)\s*===")
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


# === ANCHOR: ANCHOR_TOOLS_BUILD_ANCHOR_NAME_START ===
def build_anchor_name(path: Path) -> str:
    return re.sub(
        r"[^A-Z0-9_]", "_", path.stem.upper().replace("-", "_").replace(" ", "_")
    )


# === ANCHOR: ANCHOR_TOOLS_BUILD_ANCHOR_NAME_END ===


# === ANCHOR: ANCHOR_TOOLS_NORMALIZE_ANCHOR_NAME_START ===
def normalize_anchor_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9_]", "_", name.upper())


# === ANCHOR: ANCHOR_TOOLS_NORMALIZE_ANCHOR_NAME_END ===


# === ANCHOR: ANCHOR_TOOLS_BUILD_SYMBOL_ANCHOR_NAME_START ===
def build_symbol_anchor_name(path: Path, symbol_name: str) -> str:
    return f"{build_anchor_name(path)}_{normalize_anchor_name(symbol_name)}"


# === ANCHOR: ANCHOR_TOOLS_BUILD_SYMBOL_ANCHOR_NAME_END ===


# === ANCHOR: ANCHOR_TOOLS_BUILD_ANCHOR_BLOCK_START ===
def build_anchor_block(path: Path) -> tuple[str, str]:
    prefix = COMMENT_PREFIX.get(path.suffix.lower(), "#")
    name = build_anchor_name(path)
    return (
        f"{prefix} === ANCHOR: {name}_START ===",
        f"{prefix} === ANCHOR: {name}_END ===",
    )


# === ANCHOR: ANCHOR_TOOLS_BUILD_ANCHOR_BLOCK_END ===


# === ANCHOR: ANCHOR_TOOLS_PREVIEW_ANCHOR_TARGETS_START ===
def preview_anchor_targets(
    root: Path, allowed_exts: AllowedExts | None = None
) -> list[Path]:
    targets: list[Path] = []
    for path in iter_source_files(root):
        if allowed_exts is not None and path.suffix.lower() not in allowed_exts:
            continue
        text = safe_read_text(path)
        if text and "=== ANCHOR:" not in text:
            targets.append(path)
    return targets


# === ANCHOR: ANCHOR_TOOLS_PREVIEW_ANCHOR_TARGETS_END ===


# === ANCHOR: ANCHOR_TOOLS_ANCHOR_RECOMMENDATION_DETAILS_START ===
def anchor_recommendation_details(
    root: Path,
    path: Path,
    project_map: ProjectMapSnapshot | None = None,
    # === ANCHOR: ANCHOR_TOOLS_ANCHOR_RECOMMENDATION_DETAILS_END ===
) -> AnchorRecommendation:
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


# === ANCHOR: ANCHOR_TOOLS_RECOMMEND_ANCHOR_TARGETS_START ===
def recommend_anchor_targets(
    root: Path,
    allowed_exts: AllowedExts | None = None,
    project_map: ProjectMapSnapshot | None = None,
    # === ANCHOR: ANCHOR_TOOLS_RECOMMEND_ANCHOR_TARGETS_END ===
) -> list[AnchorRecommendation]:
    recommendations: list[AnchorRecommendation] = []
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


# === ANCHOR: ANCHOR_TOOLS__PYTHON_SYMBOL_BLOCKS_START ===
def _python_symbol_blocks(text: str) -> list[SymbolBlock]:
    lines = text.splitlines()
    blocks: list[SymbolBlock] = []
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


# === ANCHOR: ANCHOR_TOOLS__PYTHON_SYMBOL_BLOCKS_END ===


# === ANCHOR: ANCHOR_TOOLS__JS_SYMBOL_BLOCKS_START ===
def _js_symbol_blocks(text: str) -> list[SymbolBlock]:
    lines = text.splitlines()
    blocks: list[SymbolBlock] = []
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
        match: re.Match[str] | None = None
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


# === ANCHOR: ANCHOR_TOOLS__JS_SYMBOL_BLOCKS_END ===


# === ANCHOR: ANCHOR_TOOLS_INSERT_PYTHON_SYMBOL_ANCHORS_START ===
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


# === ANCHOR: ANCHOR_TOOLS_INSERT_PYTHON_SYMBOL_ANCHORS_END ===


# === ANCHOR: ANCHOR_TOOLS_INSERT_JS_SYMBOL_ANCHORS_START ===
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


# === ANCHOR: ANCHOR_TOOLS_INSERT_JS_SYMBOL_ANCHORS_END ===


# === ANCHOR: ANCHOR_TOOLS_INSERT_MODULE_ANCHORS_START ===
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
        prefix_lines: list[str] = []
        body_lines = lines
        while body_lines and (
            body_lines[0].startswith("#!")
            or body_lines[0].startswith("# -*-")
            or body_lines[0].startswith("# coding:")
        ):
            prefix_lines.append(body_lines.pop(0))
        wrapped: list[str] = []
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


# === ANCHOR: ANCHOR_TOOLS_INSERT_MODULE_ANCHORS_END ===


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHORS_START ===
def extract_anchors(path: Path) -> list[str]:
    anchors: list[str] = []
    for match in ANCHOR_RE.finditer(safe_read_text(path)):
        raw = match.group(1)
        base = re.sub(r"_(START|END)$", "", raw)
        anchors.append(base)
    return list(dict.fromkeys(anchors))


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHORS_END ===


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHOR_SPANS_START ===
def extract_anchor_spans(path: Path) -> list[dict[str, object]]:
    """각 앵커의 이름·시작줄·종료줄을 1-based 로 반환.

    `_START` 마커가 나타난 줄을 start, 매칭되는 `_END` 마커의 줄을 end 로 기록.
    짝 없는 `_END` 는 무시하고, 짝 없는 `_START` 는 end=None 으로 남긴다.
    같은 이름이 중복 시 나타난 순서대로 모두 포함.
    """
    text = safe_read_text(path)
    if not text:
        return []
    pending: dict[str, list[int]] = {}
    spans: list[dict[str, object]] = []
    seen_counts: dict[str, int] = {}
    for match in ANCHOR_RE.finditer(text):
        raw = match.group(1)
        line_no = text.count("\n", 0, match.start()) + 1
        if raw.endswith("_START"):
            base = re.sub(r"_START$", "", raw)
            seen_counts[base] = seen_counts.get(base, 0) + 1
            occurrence = seen_counts[base]
            display_name = base if occurrence == 1 else f"{base}_{occurrence}"
            pending.setdefault(base, []).append(len(spans))
            spans.append({"name": display_name, "start": line_no, "end": None})
        elif raw.endswith("_END"):
            base = re.sub(r"_END$", "", raw)
            stack = pending.get(base)
            if stack:
                idx = stack.pop()
                spans[idx]["end"] = line_no
    return [span for span in spans if span["end"] is not None]


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHOR_SPANS_END ===


# === ANCHOR: ANCHOR_TOOLS_SUGGEST_ANCHOR_NAMES_START ===
def suggest_anchor_names(path: Path) -> list[str]:
    text = safe_read_text(path)
    if not text:
        return []
    names: list[str] = []
    suffix = path.suffix.lower()
    if suffix == ".py":
        for match in PY_SYMBOL_RE.finditer(text):
            names.append(match.group(1))
    elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
        for match in JS_SYMBOL_RE.finditer(text):
            names.append(match.group(1))
        for match in CONST_FUNC_RE.finditer(text):
            names.append(match.group(1))
    normalized = [
        normalize_anchor_name(name)
        for name in names
        if name and not name.startswith("__")
    ]
    return list(dict.fromkeys(normalized[:24]))


# === ANCHOR: ANCHOR_TOOLS_SUGGEST_ANCHOR_NAMES_END ===


# === ANCHOR: ANCHOR_TOOLS_COLLECT_ANCHOR_INDEX_START ===
def collect_anchor_index(
    root: Path, allowed_exts: AllowedExts | None = None
) -> dict[str, list[str]]:
    if allowed_exts is None:
        from vibelign.core.fast_tools import has_rg, grep_anchors_rg

        if has_rg():
            result = grep_anchors_rg(root)
            if result is not None:
                return result
    index: dict[str, list[str]] = {}
    for path in iter_source_files(root):
        if allowed_exts is not None and path.suffix.lower() not in allowed_exts:
            continue
        anchors = extract_anchors(path)
        if anchors:
            index[str(path.relative_to(root))] = anchors
    return index


# === ANCHOR: ANCHOR_TOOLS_COLLECT_ANCHOR_INDEX_END ===


# === ANCHOR: ANCHOR_TOOLS_COLLECT_ANCHOR_METADATA_START ===
def collect_anchor_metadata(
    root: Path,
    allowed_exts: AllowedExts | None = None,
    # === ANCHOR: ANCHOR_TOOLS_COLLECT_ANCHOR_METADATA_END ===
) -> dict[str, AnchorMetadataEntry]:
    metadata: dict[str, AnchorMetadataEntry] = {}
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


# === ANCHOR: ANCHOR_TOOLS_LOAD_ANCHOR_META_START ===
def load_anchor_meta(root: Path) -> dict[str, AnchorMetaEntry]:
    """anchor_meta.json 로드. 없으면 빈 딕셔너리 반환."""
    from vibelign.core.meta_paths import MetaPaths

    meta = MetaPaths(root)
    if not meta.anchor_meta_path.exists():
        return {}
    try:
        raw = cast(
            object, json.loads(meta.anchor_meta_path.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError):
        return {}
    data = _normalize_object_dict(raw)
    if data is None:
        return {}
    normalized: dict[str, AnchorMetaEntry] = {}
    for key, value in data.items():
        entry = _normalize_object_dict(value)
        if entry is None:
            continue
        meta_entry: AnchorMetaEntry = {}
        intent = entry.get("intent")
        if isinstance(intent, str):
            meta_entry["intent"] = intent
        connects = _normalize_string_list(entry.get("connects"))
        if connects:
            meta_entry["connects"] = connects
        warning = entry.get("warning")
        if isinstance(warning, str):
            meta_entry["warning"] = warning
        aliases = _normalize_string_list(entry.get("aliases"))
        if aliases:
            meta_entry["aliases"] = aliases
        description = entry.get("description")
        if isinstance(description, str):
            meta_entry["description"] = description
        normalized[key] = meta_entry
    return normalized


# === ANCHOR: ANCHOR_TOOLS_LOAD_ANCHOR_META_END ===


# === ANCHOR: ANCHOR_TOOLS_SAVE_ANCHOR_META_START ===
def save_anchor_meta(root: Path, data: dict[str, AnchorMetaEntry]) -> None:
    """anchor_meta.json 저장."""
    from vibelign.core.meta_paths import MetaPaths

    meta = MetaPaths(root)
    meta.ensure_vibelign_dir()
    _ = meta.anchor_meta_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# === ANCHOR: ANCHOR_TOOLS_SAVE_ANCHOR_META_END ===


# === ANCHOR: ANCHOR_TOOLS_SET_ANCHOR_INTENT_START ===
def set_anchor_intent(
    root: Path,
    anchor_name: str,
    intent: str,
    connects: list[str] | None = None,
    warning: str | None = None,
    aliases: list[str] | None = None,
    description: str | None = None,
    # === ANCHOR: ANCHOR_TOOLS_SET_ANCHOR_INTENT_END ===
) -> None:
    """특정 앵커에 의도(intent) 정보를 저장한다."""
    data = load_anchor_meta(root)
    entry = data.get(anchor_name, {})
    entry["intent"] = intent
    if connects is not None:
        entry["connects"] = connects
    if warning is not None:
        entry["warning"] = warning
    if aliases is not None:
        entry["aliases"] = aliases
    if description is not None:
        entry["description"] = description
    data[anchor_name] = entry
    save_anchor_meta(root, data)


# === ANCHOR: ANCHOR_TOOLS_GET_ANCHOR_INTENT_START ===
def get_anchor_intent(root: Path, anchor_name: str) -> AnchorMetaEntry:
    """특정 앵커의 의도 정보를 반환. 없으면 빈 딕셔너리."""
    return load_anchor_meta(root).get(anchor_name, {})


# === ANCHOR: ANCHOR_TOOLS_GET_ANCHOR_INTENT_END ===


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHOR_LINE_RANGES_START ===
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


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHOR_LINE_RANGES_END ===


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHOR_BLOCKS_START ===
def extract_anchor_blocks(path: Path) -> dict[str, str]:
    """각 앵커의 START~END 사이 코드를 추출. {anchor_name: code}"""
    text = safe_read_text(path)
    if not text:
        return {}
    blocks: dict[str, str] = {}
    current_anchor: str | None = None
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


# === ANCHOR: ANCHOR_TOOLS_EXTRACT_ANCHOR_BLOCKS_END ===


# === ANCHOR: ANCHOR_TOOLS_GENERATE_ANCHOR_INTENTS_WITH_AI_START ===
# ─── 코드 기반 aliases 생성 ────────────────────────────────────────────────────

_REVERSE_ALIASES: dict[str, list[str]] = {}  # 영어→한국어 역방향 매핑 (lazy init)


def _get_reverse_aliases() -> dict[str, list[str]]:
    """patch_suggester의 _TOKEN_ALIASES를 역방향으로 변환. button→버튼 등."""
    if _REVERSE_ALIASES:
        return _REVERSE_ALIASES
    try:
        from vibelign.core.patch_suggester import _TOKEN_ALIASES
        for korean, english_list in _TOKEN_ALIASES.items():
            for eng in english_list:
                if eng not in _REVERSE_ALIASES:
                    _REVERSE_ALIASES[eng] = []
                if korean not in _REVERSE_ALIASES[eng]:
                    _REVERSE_ALIASES[eng].append(korean)
    except ImportError:
        pass
    return _REVERSE_ALIASES


def _split_anchor_name(anchor: str) -> list[str]:
    """MAIN_WINDOW__APPLY_BTN_STYLE → ['main', 'window', 'apply', 'btn', 'style']"""
    return [t.lower() for t in re.split(r"[_]+", anchor) if t]


_CODE_IDENT_RE = re.compile(
    r"(?:class|def|function|const|let|var|export)\s+([A-Za-z_]\w*)"
)

_ABBREV_MAP = {
    "btn": "button",
    "msg": "message",
    "cfg": "config",
    "dlg": "dialog",
    "mgr": "manager",
    "hdr": "header",
    "nav": "navigation",
    "auth": "authentication",
    "img": "image",
    "fmt": "format",
    "lbl": "label",
    "txt": "text",
}


def _extract_code_identifiers(code: str) -> list[str]:
    """코드에서 class명, 함수명 등 식별자 추출 → 소문자 토큰 리스트."""
    idents = _CODE_IDENT_RE.findall(code)
    tokens: list[str] = []
    for ident in idents:
        parts = re.findall(r"[a-z]+|[A-Z][a-z]*|[0-9]+", ident)
        tokens.extend(p.lower() for p in parts if len(p) > 1)
    return tokens


def generate_code_based_aliases(anchor: str, code: str) -> tuple[list[str], str]:
    """앵커 이름과 코드에서 규칙 기반으로 aliases/description 생성."""
    reverse = _get_reverse_aliases()
    name_tokens = _split_anchor_name(anchor)
    code_tokens = _extract_code_identifiers(code)

    # 영어 aliases: 앵커 이름 토큰 + 약어 확장
    eng_parts: list[str] = []
    for t in name_tokens:
        eng_parts.append(t)
        if t in _ABBREV_MAP:
            eng_parts.append(_ABBREV_MAP[t])

    # 한국어 aliases: 역방향 매핑
    kor_parts: list[str] = []
    for t in eng_parts + code_tokens:
        for korean in reverse.get(t, []):
            if korean not in kor_parts:
                kor_parts.append(korean)

    # aliases 조합
    aliases: list[str] = []
    # 영어 alias: 공백 연결 (앵커 이름 기반)
    eng_alias = " ".join(eng_parts[:6])
    if eng_alias:
        aliases.append(eng_alias)
    # 한국어 aliases 개별 추가
    aliases.extend(kor_parts[:4])
    # 코드 식별자 기반 영어 alias
    if code_tokens:
        code_alias = " ".join(dict.fromkeys(code_tokens[:4]))
        if code_alias and code_alias != eng_alias:
            aliases.append(code_alias)

    # description: 토큰 나열
    desc_parts = [_ABBREV_MAP.get(t, t) for t in name_tokens[:5]]
    description = " ".join(desc_parts)

    return aliases, description


def generate_code_based_intents(root: Path, paths: list[Path]) -> int:
    """코드 기반으로 모든 앵커의 aliases/description을 생성. 기존 앵커도 갱신."""
    existing = load_anchor_meta(root)
    count = 0
    for path in paths:
        for anchor, code in extract_anchor_blocks(path).items():
            aliases, description = generate_code_based_aliases(anchor, code)
            if not aliases:
                continue
            entry = existing.get(anchor, {})
            if entry.get("_source") == "ai":
                continue  # AI가 이미 보강한 항목은 코드 기반으로 덮어쓰지 않음
            entry.setdefault("intent", description)
            entry["aliases"] = aliases
            entry["description"] = description
            entry["_source"] = "code"
            existing[anchor] = entry
            count += 1
    if count:
        save_anchor_meta(root, existing)
    return count


# ─── AI 기반 aliases 보강 ──────────────────────────────────────────────────────

_BATCH_SIZE = 20  # 한 번에 AI에 보내는 앵커 수
_MAX_PARALLEL = 4  # 동시 배치 수


def _generate_batch(
    root: Path,
    batch: dict[str, str],
    generate_text_with_ai: object,
) -> dict[str, AnchorMetaEntry]:
    """앵커 배치 하나를 AI에 보내고 결과를 반환 (파일 쓰기 안 함)."""
    from typing import cast, Callable

    _gen = cast(Callable[..., tuple[str, list[str]]], generate_text_with_ai)
    anchor_list = list(batch.keys())
    numbered = "\n\n".join(
        f"[{i + 1}] {name}\n{code}" for i, (name, code) in enumerate(batch.items())
    )
    prompt = (
        "다음은 코드 파일의 각 구역(앵커)입니다.\n"
        "각 구역에 대해 JSON 배열로 출력하세요. 다른 말은 하지 마세요.\n\n"
        "각 항목 형식:\n"
        '{"anchor": "앵커이름", "intent": "한 줄 설명(10~20자)", '
        '"aliases": ["한국어 별칭1", "영어 별칭", ...], '
        '"description": "이 구역이 하는 일을 한 문장으로"}\n\n'
        "aliases 규칙:\n"
        "- 사용자가 이 구역을 수정하고 싶을 때 쓸 법한 한국어/영어 표현 2~4개\n"
        "- 코드 속 변수명, 클래스명, UI 요소명을 자연어로 풀어서 포함\n"
        "- ⚠️ 절대 금지: 앵커 이름의 단어를 영어 그대로 나열 (BUILD_PATCH_STEPS → 'build patch steps' ❌, 'match rule' ❌)\n"
        "- 영어 alias도 반드시 동의어/재표현 사용 (예: match_rule → 'find matching pattern', build_patch_steps → 'construct edit operations')\n"
        "- 한국어 alias는 사용자 관점 자연어 (예: APPLY_BTN_STYLE → '전체적용 버튼', '적용 버튼 꾸미기')\n\n"
        + numbered
    )
    text, _ = _gen(prompt, quiet=True)
    if not text:
        return {}
    results: dict[str, AnchorMetaEntry] = {}
    try:
        json_text = text.strip()
        if "```" in json_text:
            start = json_text.find("[")
            end = json_text.rfind("]") + 1
            if start >= 0 and end > start:
                json_text = json_text[start:end]
        items = json.loads(json_text)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                anchor_name = item.get("anchor", "")
                if anchor_name not in batch:
                    continue
                intent = item.get("intent", "")
                if not intent:
                    continue
                entry: AnchorMetaEntry = {"intent": intent}
                aliases = item.get("aliases")
                if isinstance(aliases, list):
                    entry["aliases"] = aliases
                description = item.get("description")
                if isinstance(description, str):
                    entry["description"] = description
                results[anchor_name] = entry
    except (json.JSONDecodeError, ValueError):
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
            results[anchor] = {"intent": intent}
    return results


def generate_anchor_intents_with_ai(
    root: Path, paths: list[Path], *, force: bool = False
) -> int:
    """AI를 사용해 anchor intent/aliases/description을 보강. 반환: 등록된 intent 수.

    이미 AI가 생성한 aliases가 있는 앵커는 건너뛴다.
    force=True이면 기존 AI 생성 항목도 재생성한다.
    배치를 최대 _MAX_PARALLEL개씩 병렬 실행한다.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from vibelign.core.ai_explain import generate_text_with_ai, has_ai_provider

    if not has_ai_provider():
        return 0
    # 이미 AI가 보강한 앵커만 건너뛰기 (코드 기반은 덮어씀)
    existing = load_anchor_meta(root)
    all_blocks: dict[str, str] = {}
    for path in paths:
        for anchor, code in extract_anchor_blocks(path).items():
            entry = existing.get(anchor, {})
            if not force and entry.get("_source") == "ai":
                continue
            all_blocks[anchor] = code[:400]
    if not all_blocks:
        return 0
    # 배치 분할 + 병렬 실행
    items = list(all_blocks.items())
    batches = [
        dict(items[start : start + _BATCH_SIZE])
        for start in range(0, len(items), _BATCH_SIZE)
    ]
    all_results: dict[str, AnchorMetaEntry] = {}
    with ThreadPoolExecutor(max_workers=_MAX_PARALLEL) as pool:
        futures = {
            pool.submit(_generate_batch, root, batch, generate_text_with_ai): i
            for i, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            try:
                all_results.update(future.result())
            except Exception:
                continue
    if all_results:
        data = load_anchor_meta(root)
        for anchor, entry in all_results.items():
            merged = data.get(anchor, {})
            merged.update(entry)
            merged["_source"] = "ai"
            data[anchor] = merged
        save_anchor_meta(root, data)
    return len(all_results)


# === ANCHOR: ANCHOR_TOOLS_GENERATE_ANCHOR_INTENTS_WITH_AI_END ===


# === ANCHOR: ANCHOR_TOOLS_STRIP_ANCHORS_START ===
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
        _ = path.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")
    except OSError as e:
        print(f"경고: {path} 앵커 제거 실패: {e}")
        return False
    return True


# === ANCHOR: ANCHOR_TOOLS_STRIP_ANCHORS_END ===


# === ANCHOR: ANCHOR_TOOLS_VALIDATE_ANCHOR_FILE_START ===
def validate_anchor_file(path: Path) -> list[str]:
    text = safe_read_text(path)
    if not text:
        return ["파일 내용을 읽을 수 없습니다."]
    start_markers: list[str] = re.findall(r"ANCHOR:\s*([A-Z0-9_]+)_START\s*===", text)
    end_markers: list[str] = re.findall(r"ANCHOR:\s*([A-Z0-9_]+)_END\s*===", text)
    problems: list[str] = []
    for name in start_markers:
        if name not in end_markers:
            problems.append(f"{name}_START 에 대응하는 END 가 없습니다")
    for name in end_markers:
        if name not in start_markers:
            problems.append(f"{name}_END 에 대응하는 START 가 없습니다")
    if not start_markers and not end_markers:
        problems.append("앵커가 없습니다")
    return problems


# === ANCHOR: ANCHOR_TOOLS_VALIDATE_ANCHOR_FILE_END ===
# === ANCHOR: ANCHOR_TOOLS_END ===
