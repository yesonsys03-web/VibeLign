# === ANCHOR: PATCH_SUGGESTER_START ===
from pathlib import Path
import re
import json
from dataclasses import dataclass, asdict
from typing import Optional
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import ProjectMapSnapshot, load_project_map
from vibelign.core.project_scan import iter_source_files, relpath_str
from vibelign.core.anchor_tools import extract_anchors

KEYWORD_HINTS = {
    "progress": [
        "progress",
        "worker",
        "backup",
        "copy",
        "ui",
        "status",
        "render",
        "widget",
        "panel",
        "terminal",
    ],
    "backup": ["backup", "worker", "copy", "hash", "verify"],
    "ui": ["ui", "window", "dialog", "widget", "layout", "button"],
    "button": ["button", "ui", "window", "dialog", "layout"],
    "log": ["log", "logger", "logging", "status"],
    "schedule": ["schedule", "scheduler", "cron", "timer"],
    "config": ["config", "settings", "json", "yaml", "toml"],
    # 한국어 키워드
    "버튼": ["button", "ui", "window", "dialog", "layout"],
    "색상": ["ui", "window", "dialog", "widget", "layout", "button"],
    "화면": ["ui", "window", "dialog", "widget", "layout", "panel"],
    "창": ["ui", "window", "dialog", "widget"],
    "레이아웃": ["ui", "window", "dialog", "layout"],
    "로그": ["log", "logger", "logging", "status"],
    "설정": ["config", "settings", "json", "yaml", "toml"],
}

LOW_PRIORITY_NAMES = {"__init__.py", "__init__.js", "__init__.ts"}


@dataclass
class PatchSuggestion:
    request: str
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]

    def to_dict(self):
        return asdict(self)


def tokenize(text):
    return re.findall(r"[a-zA-Z_]+|[가-힣]+", text.lower())


def _score_anchor_names(anchor_names, request_tokens, label):
    score = 0
    rationale = []
    for anchor in anchor_names:
        al = anchor.lower()
        local_score = 0
        local_matches = []
        match_count = 0
        for token in request_tokens:
            if token in al:
                local_score += 3
                match_count += 1
                local_matches.append(token)
        if label == "추천 앵커":
            if anchor.startswith("_"):
                local_score -= 2
            if any(
                part in al
                for part in [
                    "load",
                    "get",
                    "build",
                    "run",
                    "parse",
                    "flush",
                    "normalize",
                ]
            ):
                local_score -= 1
            if match_count < 2:
                local_score -= 3
        if local_score > 0:
            score = max(score, local_score)
            joined = ", ".join(dict.fromkeys(local_matches))
            rationale = [f"{label} '{anchor}'에 키워드 {joined} 이(가) 포함됨"]
    return score, rationale


_UI_REQUEST_KEYWORDS = [
    "progress", "ui", "button", "dialog", "window", "layout",
    "sidebar", "panel", "widget", "screen", "render",
    "버튼", "색상", "화면", "창", "레이아웃", "디자인", "스타일", "폰트", "크기", "컬러", "사이즈",
]


def _is_ui_request(request_tokens):
    return any(
        any(kw in tok or tok in kw for kw in _UI_REQUEST_KEYWORDS)
        for tok in request_tokens
    )


def _is_service_request(request_tokens):
    return any(
        tok in request_tokens
        for tok in ["service", "auth", "login", "api", "worker", "guard", "schedule"]
    )


def score_path(
    path: Path,
    request_tokens,
    rel_path: str,
    anchor_meta=None,
    project_map: Optional[ProjectMapSnapshot] = None,
    intent_meta: Optional[dict] = None,
):
    score = 0
    rationale = []
    pt = str(path).lower()
    stem = path.stem.lower()

    if path.name in LOW_PRIORITY_NAMES:
        score -= 6
        rationale.append("init 스타일 파일이라 우선순위 낮음")
    if (
        "/tests/" in pt
        or pt.startswith("tests/")
        or "/docs/" in pt
        or pt.startswith("docs/")
    ):
        score -= 5
        rationale.append("docs/test 경로라 우선순위 낮음")

    for token in request_tokens:
        if token and token in pt:
            score += 3
            rationale.append(f"경로에 키워드 '{token}'이 포함됨")
    for key, hints in KEYWORD_HINTS.items():
        if key in request_tokens:
            for hint in hints:
                if hint in pt:
                    score += 2
                    rationale.append(f"'{key}' 키워드 계열인 '{hint}'와 경로가 일치")
    if stem in request_tokens:
        score += 4
        rationale.append(f"파일명 '{stem}'이 요청과 직접 일치")
    ui_request = _is_ui_request(request_tokens)
    if ui_request and any(
        tok in pt
        for tok in ["ui", "window", "dialog", "widget", "render", "terminal", "panel"]
    ):
        score += 3
        rationale.append("UI 성격 요청과 경로 특성이 잘 맞음")
    if project_map is not None:
        map_kind = project_map.classify_path(rel_path)
        if rel_path in project_map.entry_files and not any(
            tok in request_tokens for tok in ["main", "entry", "startup", "boot", "cli"]
        ):
            score -= 2
            rationale.append("entry file 은 꼭 필요할 때만 건드리는 편이 안전함")
        if ui_request and map_kind == "ui":
            score += 4
            rationale.append("Project Map 에서 UI 모듈로 분류된 파일임")
        if _is_service_request(request_tokens) and map_kind == "service":
            score += 4
            rationale.append("Project Map 에서 service 모듈로 분류된 파일임")
        if map_kind == "logic" and not ui_request:
            score += 2
            rationale.append("Project Map 에서 core/logic 모듈로 분류된 파일임")
        if rel_path in project_map.large_files:
            score += 1
            rationale.append(
                "Project Map 에서 큰 파일로 표시되어 수정 후보로 우선 검토함"
            )
    if any(
        tok in stem for tok in ["worker", "service", "window", "scheduler", "backup"]
    ):
        score += 1
    if isinstance(anchor_meta, dict):
        real_anchor_score, real_anchor_rationale = _score_anchor_names(
            anchor_meta.get("anchors", []), request_tokens, "실제 앵커"
        )
        suggested_score, suggested_rationale = _score_anchor_names(
            anchor_meta.get("suggested_anchors", []), request_tokens, "추천 앵커"
        )
        if real_anchor_score:
            score += real_anchor_score + 6
            rationale.extend(real_anchor_rationale)
        elif suggested_score:
            score += suggested_score + 2
            rationale.extend(suggested_rationale)
    if isinstance(intent_meta, dict):
        for anchor_name, meta_entry in intent_meta.items():
            intent = meta_entry.get("intent", "").lower()
            if not intent:
                continue
            intent_tokens = re.findall(r"[a-zA-Z_가-힣]+", intent)
            matched = [t for t in request_tokens if t in intent_tokens or t in intent]
            if matched:
                score += len(matched) * 3
                rationale.append(f"앵커 intent에 키워드 '{', '.join(matched)}'이 포함됨")
                break
    return score, rationale


_UI_STYLE_TOKENS = {"색상", "주황색", "파란색", "빨간색", "초록색", "노란색", "보라색", "폰트", "스타일", "디자인", "크기", "굵기", "투명도", "배경색", "글자색", "컬러", "사이즈", "보색"}
_LOGIC_INTENT_TOKENS = {"번역", "api", "번역문", "번역기", "변환", "처리", "관리", "요청", "응답", "저장", "로드"}


def _has_style_token(request_tokens) -> bool:
    """조사가 붙은 토큰도 포함해서 스타일 키워드 존재 여부 확인"""
    return any(style in tok for tok in request_tokens for style in _UI_STYLE_TOKENS)


def choose_anchor(anchors, request_tokens, anchor_meta: Optional[dict] = None):
    if not anchors:
        return "[먼저 앵커를 추가하세요]", ["이 파일에는 아직 앵커가 없습니다"]
    is_style_request = _has_style_token(request_tokens)
    best_anchor = anchors[0]
    best_score = -1
    best_rationale = [f"첫 번째 앵커 '{best_anchor}'를 기본값으로 선택"]
    for anchor in anchors:
        score = 0
        rationale = []
        al = anchor.lower()
        for token in request_tokens:
            if token in al:
                score += 3
                rationale.append(f"앵커에 키워드 '{token}'이 포함됨")
        if "core" in al or "logic" in al or "worker" in al:
            score += 1
        # intent 정보가 있으면 자연어 매칭 점수 추가
        if anchor_meta and anchor in anchor_meta:
            meta = anchor_meta[anchor]
            intent = meta.get("intent", "").lower()
            if intent:
                intent_tokens = re.findall(r"[a-zA-Z_가-힣]+", intent)
                for token in request_tokens:
                    if token in intent_tokens or token in intent:
                        score += 4
                        rationale.append(
                            f"앵커 의도('{intent[:30]}...')에 키워드 '{token}'이 포함됨"
                            if len(intent) > 30
                            else f"앵커 의도('{intent}')에 키워드 '{token}'이 포함됨"
                        )
                # 스타일 요청인데 intent가 로직 성격이면 페널티
                if is_style_request and any(t in intent for t in _LOGIC_INTENT_TOKENS):
                    score -= 5
                    rationale.append("스타일 요청인데 로직 성격 앵커라 우선순위 낮춤")
            warning = meta.get("warning")
            if warning:
                rationale.append(f"⚠️ {warning}")
        if score > best_score:
            best_score = score
            best_anchor = anchor
            best_rationale = rationale or [
                f"사용 가능한 앵커 중 '{anchor}'를 최선으로 선택"
            ]
    return best_anchor, best_rationale


def choose_suggested_anchor(suggested_anchors, request_tokens):
    if not suggested_anchors:
        return None, []
    best_anchor = suggested_anchors[0]
    best_score = -1
    best_rationale = [f"추천 앵커 '{best_anchor}'를 기본값으로 선택"]
    for anchor in suggested_anchors:
        score = 0
        rationale = []
        al = anchor.lower()
        match_count = 0
        for token in request_tokens:
            if token in al:
                score += 3
                match_count += 1
                rationale.append(f"추천 앵커에 키워드 '{token}'이 포함됨")
        if anchor.startswith("_"):
            score -= 2
            rationale.append("내부 helper 성격 이름이라 우선순위 낮춤")
        if any(
            part in al
            for part in ["load", "get", "build", "run", "parse", "flush", "normalize"]
        ):
            score -= 1
            rationale.append("범용 helper 성격 이름이라 우선순위 낮춤")
        if match_count < 2:
            score -= 3
            rationale.append("요청 키워드가 충분히 많이 맞지 않아 추천 강도를 낮춤")
        if score > best_score:
            best_score = score
            best_anchor = anchor
            best_rationale = rationale or [f"추천 앵커 중 '{anchor}'가 가장 적합함"]
    if best_score <= 0:
        return None, ["의미 있게 맞는 추천 앵커를 찾지 못했습니다"]
    return best_anchor, best_rationale


def load_anchor_metadata(root: Path):
    meta = MetaPaths(root)
    if not meta.anchor_index_path.exists():
        return {}
    try:
        payload = json.loads(meta.anchor_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    files = payload.get("files", {})
    return files if isinstance(files, dict) else {}


def suggest_patch(root: Path, request: str):
    from vibelign.core.anchor_tools import load_anchor_meta
    request_tokens = tokenize(request)
    metadata = load_anchor_metadata(root)
    anchor_meta = load_anchor_meta(root)
    project_map, _project_map_error = load_project_map(root)
    scored = []
    for path in iter_source_files(root):
        rel = relpath_str(root, path)
        score, rationale = score_path(
            path,
            request_tokens,
            rel,
            metadata.get(rel, {}),
            project_map,
            intent_meta=anchor_meta,
        )
        scored.append((score, path, rationale))

    if not scored:
        return PatchSuggestion(
            request,
            "[소스 파일 없음]",
            "[없음]",
            "low",
            ["프로젝트에 아직 소스 파일이 없습니다"],
        )

    scored.sort(key=lambda x: (-x[0], str(x[1])))
    best_score, best_path, reasons = scored[0]
    anchors = extract_anchors(best_path)
    anchor, ar = choose_anchor(anchors, request_tokens, anchor_meta)
    if anchor == "[먼저 앵커를 추가하세요]":
        file_meta = metadata.get(relpath_str(root, best_path), {}) if metadata else {}
        suggested = (
            file_meta.get("suggested_anchors", [])
            if isinstance(file_meta, dict)
            else []
        )
        suggested_anchor, suggested_rationale = choose_suggested_anchor(
            suggested, request_tokens
        )
        if suggested_anchor:
            anchor = f"[추천 앵커: {suggested_anchor}]"
            ar = suggested_rationale
    confidence = "high" if best_score >= 8 else "medium" if best_score >= 4 else "low"
    return PatchSuggestion(
        request, relpath_str(root, best_path), anchor, confidence, reasons[:5] + ar[:3]
    )


# === ANCHOR: PATCH_SUGGESTER_END ===
