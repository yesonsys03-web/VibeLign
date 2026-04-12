# === ANCHOR: STRUCTURE_PLANNER_START ===
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from vibelign.core.project_map import load_project_map

_MAX_INLINE_EDIT_LINES = 20
_NEW_FILE_LINE_THRESHOLD = 150


@dataclass(frozen=True)
# === ANCHOR: STRUCTURE_PLANNER_PLANNERRULE_START ===
class PlannerRule:
    tokens: tuple[str, ...]
    target_category: str
    default_filename: str
    path_signals: tuple[str, ...]
    preferred_existing_names: tuple[str, ...] = ()
# === ANCHOR: STRUCTURE_PLANNER_PLANNERRULE_END ===


_CATEGORY_PATHS: dict[str, str] = {
    "core": "vibelign/core",
    "service": "vibelign/core",
    "ui": "vibelign",
    "entry": "vibelign",
    "commands": "vibelign/commands",
    "mcp": "vibelign/mcp",
    "tests": "tests",
    "docs": "docs",
}

_KEYWORD_RULES: tuple[PlannerRule, ...] = (
    PlannerRule(
        tokens=("oauth", "auth", "login", "token"),
        target_category="core",
        default_filename="oauth_provider.py",
        path_signals=("auth", "oauth", "token"),
        preferred_existing_names=("auth.py", "auth_handler.py"),
    ),
    PlannerRule(
        tokens=("watch", "monitor", "scan"),
        target_category="core",
        default_filename="watch_extension.py",
        path_signals=("watch",),
        preferred_existing_names=("watch_engine.py",),
    ),
    PlannerRule(
        tokens=("mcp", "handler"),
        target_category="mcp",
        default_filename="mcp_feature_handler.py",
        path_signals=("mcp", "handler"),
        preferred_existing_names=("mcp_patch_handlers.py", "mcp_misc_handlers.py"),
    ),
    PlannerRule(
        tokens=("cli", "command"),
        target_category="commands",
        default_filename="feature_command.py",
        path_signals=("command", "cli"),
    ),
    PlannerRule(
        tokens=("test", "spec"),
        target_category="tests",
        default_filename="test_new_feature.py",
        path_signals=("test",),
    ),
    PlannerRule(
        tokens=("doc", "docs", "readme", "manual"),
        target_category="docs",
        default_filename="feature.md",
        path_signals=("doc", "readme", "manual"),
    ),
)


# === ANCHOR: STRUCTURE_PLANNER__NOW_ISO_START ===
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
# === ANCHOR: STRUCTURE_PLANNER__NOW_ISO_END ===


# === ANCHOR: STRUCTURE_PLANNER__SLUGIFY_FEATURE_START ===
def _slugify_feature(feature: str) -> str:
    ascii_tokens = cast(list[str], re.findall(r"[a-z0-9]+", feature.lower()))
    if ascii_tokens:
        return "_".join(ascii_tokens[:4])
    return "new_feature"
# === ANCHOR: STRUCTURE_PLANNER__SLUGIFY_FEATURE_END ===


# === ANCHOR: STRUCTURE_PLANNER__EXTRACT_KEYWORDS_START ===
def _extract_keywords(feature: str) -> list[str]:
    seen: set[str] = set()
    keywords: list[str] = []
    tokens = cast(list[str], re.findall(r"[A-Za-z0-9가-힣_]+", feature.lower()))
    for token in tokens:
        if token not in seen:
            seen.add(token)
            keywords.append(token)
    return keywords
# === ANCHOR: STRUCTURE_PLANNER__EXTRACT_KEYWORDS_END ===


# === ANCHOR: STRUCTURE_PLANNER__MATCH_RULE_START ===
def _match_rule(keywords: list[str]) -> tuple[PlannerRule, list[str]]:
    for rule in _KEYWORD_RULES:
        matched = [token for token in keywords if token in rule.tokens]
        if matched:
            return rule, matched
    return (
        PlannerRule(
            tokens=(),
            target_category="core",
            default_filename="new_feature.py",
            path_signals=(),
        ),
        [],
    )
# === ANCHOR: STRUCTURE_PLANNER__MATCH_RULE_END ===


# === ANCHOR: STRUCTURE_PLANNER__ITER_CANDIDATE_FILES_START ===
def _iter_candidate_files(
    files: dict[str, dict[str, object]],
    scope: str | None,
# === ANCHOR: STRUCTURE_PLANNER__ITER_CANDIDATE_FILES_END ===
) -> list[tuple[str, dict[str, object]]]:
    normalized_scope = (scope or "").strip().replace("\\", "/")
    candidates: list[tuple[str, dict[str, object]]] = []
    for path, data in files.items():
        if normalized_scope and not path.startswith(normalized_scope):
            continue
        candidates.append((path, data))
    return candidates


# === ANCHOR: STRUCTURE_PLANNER__PATH_MATCH_SIGNALS_START ===
def _path_match_signals(path: str, rule: PlannerRule, keywords: list[str]) -> list[str]:
    lowered = path.lower()
    matches: list[str] = []
    for signal in rule.path_signals:
        if signal in lowered and signal not in matches:
            matches.append(signal)
    for keyword in keywords:
        if keyword and keyword in lowered and keyword not in matches:
            matches.append(keyword)
    return matches
# === ANCHOR: STRUCTURE_PLANNER__PATH_MATCH_SIGNALS_END ===


# === ANCHOR: STRUCTURE_PLANNER__CANDIDATE_HAS_ANCHORS_START ===
def _candidate_has_anchors(
    path: str,
    data: dict[str, object],
    anchor_index: dict[str, list[str]],
# === ANCHOR: STRUCTURE_PLANNER__CANDIDATE_HAS_ANCHORS_END ===
) -> bool:
    anchors_obj = data.get("anchors")
    if isinstance(anchors_obj, list) and anchors_obj:
        return True
    return bool(anchor_index.get(path, []))


# === ANCHOR: STRUCTURE_PLANNER__CHOOSE_EXISTING_FILE_START ===
def _choose_existing_file(
    candidates: list[tuple[str, dict[str, object]]],
    keywords: list[str],
    rule: PlannerRule,
    anchor_index: dict[str, list[str]],
# === ANCHOR: STRUCTURE_PLANNER__CHOOSE_EXISTING_FILE_END ===
) -> tuple[str | None, dict[str, object] | None, list[str]]:
    scored: list[tuple[int, str, dict[str, object]]] = []
    for path, data in candidates:
        score = 0
        lowered = path.lower()
        matched_signals = _path_match_signals(path, rule, keywords)
        preferred_name_match = Path(path).name in rule.preferred_existing_names
        has_anchors = _candidate_has_anchors(path, data, anchor_index)
        category = str(data.get("category", ""))
        if category == rule.target_category:
            score += 4
        if matched_signals:
            score += 4
        if preferred_name_match:
            score += 5
        if any(keyword and keyword in lowered for keyword in keywords):
            score += 6
        if has_anchors:
            score += 2
        line_count = data.get("line_count")
        if isinstance(line_count, int) and line_count <= _NEW_FILE_LINE_THRESHOLD:
            score += 1
        if has_anchors and (preferred_name_match or matched_signals) and score >= 5:
            scored.append((score, path, data))
    if not scored:
        return None, None, []
    scored.sort(key=lambda item: (-item[0], item[1]))
    narrowed_candidates = [path for _, path, _ in scored[:10]]
    _, path, data = scored[0]
    return path, data, narrowed_candidates


# === ANCHOR: STRUCTURE_PLANNER__LOAD_ANCHORS_START ===
def _load_anchors(
    existing_path: str,
    existing_data: dict[str, object],
    anchor_index: dict[str, list[str]],
# === ANCHOR: STRUCTURE_PLANNER__LOAD_ANCHORS_END ===
) -> list[str]:
    anchors_obj = existing_data.get("anchors", [])
    if isinstance(anchors_obj, list) and anchors_obj:
        return [str(item) for item in cast(list[object], anchors_obj)]
    indexed = anchor_index.get(existing_path, [])
    return [str(item) for item in indexed]


# === ANCHOR: STRUCTURE_PLANNER__PICK_ANCHOR_START ===
def _pick_anchor(
    path: str,
    anchors: list[str],
    keywords: list[str],
    rule: PlannerRule,
    matched_path_signals: list[str],
# === ANCHOR: STRUCTURE_PLANNER__PICK_ANCHOR_END ===
) -> tuple[str | None, str | None]:
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    for anchor in anchors:
        lowered_anchor = anchor.lower()
        if any(keyword in lowered_anchor for keyword in lowered_keywords):
            return anchor, "keyword_anchor_match"
    preferred_name_match = Path(path).name in rule.preferred_existing_names
    if anchors and (preferred_name_match or len(matched_path_signals) >= 2):
        return anchors[0], "strong_path_signal_fallback"
    return None, None


# === ANCHOR: STRUCTURE_PLANNER_BUILD_STRUCTURE_PLAN_START ===
def build_structure_plan(
    root: Path,
    feature: str,
    *,
    mode: str = "rules",
    scope: str | None = None,
# === ANCHOR: STRUCTURE_PLANNER_BUILD_STRUCTURE_PLAN_END ===
) -> dict[str, object]:
    keywords = _extract_keywords(feature)
    rule, matched_keywords = _match_rule(keywords)
    snapshot, _error = load_project_map(root)
    files = snapshot.files if snapshot is not None else {}
    anchor_index = snapshot.anchor_index if snapshot is not None else {}
    candidates = _iter_candidate_files(files, scope)
    existing_path, existing_data, narrowed_candidates = _choose_existing_file(
        candidates, keywords, rule, anchor_index
    )

    target_dir = _CATEGORY_PATHS[rule.target_category]
    default_slug = _slugify_feature(feature)
    filename = rule.default_filename
    if filename == "new_feature.py" and target_dir not in {"docs", "tests"}:
        filename = f"{default_slug}.py"
    new_file_path = f"{target_dir}/{filename}"

    plan_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{default_slug}"
    created_at = _now_iso()

    allowed_modifications: list[dict[str, object]] = []
    existing_file_paths: list[str] = []
    matched_categories: list[str] = []
    matched_path_signals: list[str] = []
    anchor_selection_reason: str | None = None
    if existing_path is not None and existing_data is not None:
        existing_file_paths.append(existing_path)
        category = str(existing_data.get("category", ""))
        if category:
            matched_categories.append(category)
        matched_path_signals = _path_match_signals(existing_path, rule, keywords)
        anchors = _load_anchors(existing_path, existing_data, anchor_index)
        selected_anchor, anchor_selection_reason = _pick_anchor(
            existing_path, anchors, keywords, rule, matched_path_signals
        )
        if selected_anchor is not None:
            allowed_modifications.append(
                {
                    "path": existing_path,
                    "anchor": selected_anchor,
                    "reason": "기존 진입점 또는 관련 모듈 연결",
                    "max_lines_added": _MAX_INLINE_EDIT_LINES,
                    "allowed_change_types": ["edit", "import_wiring"],
                }
            )

    required_new_files: list[dict[str, object]] = []
    required_reasons: list[str] = []
    if not allowed_modifications or (
        isinstance(existing_data, dict)
        and isinstance(existing_data.get("line_count"), int)
        and cast(int, existing_data.get("line_count")) > _NEW_FILE_LINE_THRESHOLD
    ):
        required_new_files.append(
            {
                "path": new_file_path,
                "responsibility": f"{feature} 기능 구현",
            }
        )
        required_reasons.append("new_production_file")
    if existing_path is not None and not allowed_modifications:
        required_reasons.append("no_matching_anchor")
    if len(existing_file_paths) >= 1 and required_new_files:
        required_reasons.append("multi_file_production_edit")
    if not required_reasons:
        required_reasons.append("single_file_planned_edit")

    forbidden: list[dict[str, object]] = []
    if existing_path is not None and required_new_files and allowed_modifications:
        allowed_anchor = str(allowed_modifications[0]["anchor"])
        forbidden.append(
            {
                "type": "path_edit_outside_allowed_anchor",
                "path": existing_path,
                "anchor": allowed_anchor,
                "reason": f"{Path(existing_path).name}에서는 {allowed_anchor} wiring만 허용하고 기능 구현 본문 추가는 제한",
            }
        )

    changed_path_classes = (
        ["support_path"] if target_dir in {"docs", "tests"} else ["production_path"]
    )
    summary_parts: list[str] = []
    if required_new_files:
        summary_parts.append("신규 파일 생성")
    if allowed_modifications:
        summary_parts.append("기존 파일 wiring 허용")
    if not summary_parts:
        summary_parts.append("근거 부족으로 보수적 신규 파일 계획")

    planner_warnings: list[str] = []
    if snapshot is None:
        planner_warnings.append(
            "project_map이 없습니다. 경로 패턴 기반으로만 분석했습니다. 정확도를 높이려면 vib watch 또는 vib scan을 사용하세요."
        )
    if not matched_keywords:
        planner_warnings.append(
            "기능 설명의 규칙 기반 키워드 근거가 약합니다. 더 구체적으로 설명하거나 --ai 옵션을 고려하세요."
        )

    summary_detail: list[str] = []
    if allowed_modifications:
        summary_detail.append(f"기존 파일 {existing_path} 연결")
    if required_new_files:
        summary_detail.append(f"신규 파일 {new_file_path} 생성")
    if not summary_detail:
        summary_detail.append("보수적 신규 파일 계획")

    return {
        "id": plan_id,
        "schema_version": 1,
        "feature": feature,
        "created_at": created_at,
        "mode": mode,
        "evidence": {
            "candidate_files": narrowed_candidates,
            "matched_categories": matched_categories,
            "matched_keywords": matched_keywords,
            "path_signals": matched_path_signals,
            "anchor_selection": anchor_selection_reason,
            "requires_planning": True,
            "required_reasons": required_reasons,
        },
        "scope": {
            "changed_path_classes": changed_path_classes,
            "new_file_paths": [item["path"] for item in required_new_files],
            "existing_file_paths": existing_file_paths,
        },
        "allowed_modifications": allowed_modifications,
        "required_new_files": required_new_files,
        "forbidden": forbidden,
        "messages": {
            "summary": f"{feature}: {', '.join(summary_parts)} ({', '.join(summary_detail)})",
            "developer_hint": "plan JSON을 저장한 뒤 state.json의 planning.active와 plan_id를 함께 갱신하세요.",
            "warnings": planner_warnings,
        },
    }
# === ANCHOR: STRUCTURE_PLANNER_END ===
