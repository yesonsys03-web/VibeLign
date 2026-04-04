# === ANCHOR: PATCH_SUGGESTER_START ===
from pathlib import Path
import re
import json
import importlib
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Optional, Union
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import ProjectMapSnapshot, load_project_map
from vibelign.core.project_scan import iter_source_files, relpath_str
from vibelign.core.anchor_tools import extract_anchors
from vibelign.core.ui_label_index import load_ui_label_index, score_boost_for_ui_labels

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

# UI 관련 path token boost는 프론트엔드 파일에만 적용
_FRONTEND_EXTS = {".tsx", ".jsx", ".vue", ".svelte", ".html", ".ts", ".js"}


@dataclass
class PatchSuggestion:
    request: str
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]

    def to_dict(self):
        return asdict(self)


_KOREAN_PARTICLE_SUFFIXES = (
    "입니다",
    "으로",
    "에서",
    "에게",
    "께서",
    "한테",
    "까지",
    "부터",
    "처럼",
    "보다",
    "라고",
    "이라",
    "라서",
    "이다",
    "였다",
    "했다",
    "하면",
    "하며",
    "하고",
    "이고",
    "이며",
    "와는",
    "과는",
    "와의",
    "과의",
    "에는",
    "와",
    "과",
    "을",
    "를",
    "이",
    "가",
    "은",
    "는",
    "에",
    "로",
    "도",
    "만",
    "의",
)

_TOKEN_ALIASES = {
    "홈": ["home"],
    "홈화면": ["home", "screen", "page"],
    "메인화면": ["main", "home", "screen", "page"],
    "화면": ["screen", "page"],
    "첫화면": ["onboarding", "screen"],
    "시작화면": ["onboarding", "screen"],
    "버전": ["version"],
    "설정": ["settings", "config"],
    "설치": ["install"],
    "안내": ["guide"],
    "가이드": ["guide"],
}

_LOW_SIGNAL_TOKENS = {
    "name",
    "function",
    "module",
    "file",
    "page",
    "screen",
    "component",
    "cmd",
    "run",
    "main",
    "lib",
    "src",
    "app",
}


def _split_identifier_parts(text: str) -> list[str]:
    parts = re.findall(r"[a-z]+|[0-9]+|[가-힣]+", text.lower())
    return [part for part in parts if part]


def _normalize_korean_token(token: str) -> list[str]:
    values = [token]
    for suffix in sorted(_KOREAN_PARTICLE_SUFFIXES, key=len, reverse=True):
        if len(token) > len(suffix) + 1 and token.endswith(suffix):
            trimmed = token[: -len(suffix)]
            values.append(trimmed)
            break
    return values


def _expand_token(token: str) -> list[str]:
    expanded: list[str] = []
    for candidate in _normalize_korean_token(token):
        expanded.append(candidate)
        expanded.extend(_split_identifier_parts(candidate))
        expanded.extend(_TOKEN_ALIASES.get(candidate, []))
    seen: set[str] = set()
    result: list[str] = []
    for item in expanded:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def tokenize(text: str) -> list[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9_]+|[가-힣]+", text.lower())
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in raw_tokens:
        for token in _expand_token(raw):
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return tokens


def _path_tokens(path: Union[Path, str]) -> set[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9]+|[가-힣]+", str(path).lower())
    tokens: set[str] = set()
    for raw in raw_tokens:
        for token in _expand_token(raw):
            tokens.add(token)
    return tokens


def _meaningful_overlap(
    request_tokens: Iterable[str], candidate_tokens: Iterable[str]
) -> list[str]:
    candidate_set = set(candidate_tokens)
    matches = [token for token in request_tokens if token in candidate_set]
    return list(dict.fromkeys(matches))


def _intent_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-zA-Z0-9_]+|[가-힣]+", text.lower()):
        for token in _expand_token(raw):
            tokens.add(token)
    return tokens


def _anchor_quality_penalty(anchor_tokens: set[str]) -> int:
    informative = [token for token in anchor_tokens if token not in _LOW_SIGNAL_TOKENS]
    if not informative:
        return 3
    if len(informative) == 1 and len(next(iter(informative), "")) <= 3:
        return 1
    return 0


def _score_anchor_names(
    anchor_names: Iterable[str], request_tokens: Iterable[str], label: str
) -> tuple[int, list[str]]:
    score = 0
    rationale = []
    for anchor in anchor_names:
        anchor_tokens = _path_tokens(anchor)
        local_score = 0
        local_matches = _meaningful_overlap(request_tokens, anchor_tokens)
        match_count = len(local_matches)
        local_score += match_count * 3
        if label == "추천 앵커":
            if anchor.startswith("_"):
                local_score -= 2
            if any(
                part in anchor_tokens
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
        else:
            local_score -= _anchor_quality_penalty(anchor_tokens)
        if local_score > 0:
            score = max(score, local_score)
            joined = ", ".join(dict.fromkeys(local_matches))
            rationale = [f"{label} '{anchor}'에 키워드 {joined} 이(가) 포함됨"]
    return score, rationale


_UI_REQUEST_KEYWORDS = [
    "progress",
    "ui",
    "button",
    "card",
    "dialog",
    "window",
    "layout",
    "sidebar",
    "panel",
    "widget",
    "screen",
    "render",
    "버튼",
    "색상",
    "화면",
    "창",
    "레이아웃",
    "디자인",
    "스타일",
    "폰트",
    "크기",
    "컬러",
    "사이즈",
    "카드",
]

_NAVIGATION_REQUEST_KEYWORDS = {
    "menu",
    "nav",
    "tab",
    "header",
    "toolbar",
    "sidebar",
    "navbar",
    "상단",
    "메뉴",
    "탭",
    "네비게이션",
    "탑",
}

_NAVIGATION_FILE_HINTS = {
    "app",
    "layout",
    "nav",
    "navbar",
    "header",
    "menu",
    "toolbar",
    "sidebar",
}

_CHROME_FILE_HINTS = {
    "titlebar",
    "title-bar",
    "window",
    "windowcontrols",
    "window-controls",
    "chrome",
    "frame",
    "shell",
}

_BACKEND_CHECKPOINT_HINTS = {
    "checkpoint",
    "checkpoints",
    "local_checkpoints",
    "rollback",
    "restore",
    "backup",
}

_COMMAND_FILE_HINTS = {
    "cmd",
    "command",
    "cli",
    "secrets",
    "doctor",
    "anchor",
    "patch",
    "guard",
    "scan",
}


def _is_ui_request(request_tokens: Iterable[str]) -> bool:
    token_set = set(request_tokens)
    return any(kw in token_set for kw in _UI_REQUEST_KEYWORDS)


def _is_service_request(request_tokens: Iterable[str]) -> bool:
    return any(
        tok in request_tokens
        for tok in ["service", "auth", "login", "api", "worker", "guard", "schedule"]
    )


def _is_navigation_request(request_tokens: Iterable[str]) -> bool:
    token_set = set(request_tokens)
    return any(kw in token_set for kw in _NAVIGATION_REQUEST_KEYWORDS)


def score_path(
    path: Path,
    request_tokens: list[str],
    rel_path: str,
    anchor_meta: Optional[dict[str, list[str]]] = None,
    project_map: Optional[ProjectMapSnapshot] = None,
    intent_meta: Optional[dict[str, dict[str, Any]]] = None,
) -> tuple[int, list[str]]:
    score = 0
    rationale = []
    pt = str(path).lower()
    stem = path.stem.lower()
    path_tokens = _path_tokens(rel_path)

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

    path_matches = _meaningful_overlap(request_tokens, path_tokens)
    for token in path_matches:
        if token:
            score += 3
            rationale.append(f"경로에 키워드 '{token}'이 포함됨")
    is_frontend = path.suffix.lower() in _FRONTEND_EXTS
    for key, hints in KEYWORD_HINTS.items():
        if key in request_tokens:
            for hint in hints:
                if hint in path_tokens:
                    if hint == "ui" and not is_frontend:
                        continue
                    score += 2
                    rationale.append(f"'{key}' 키워드 계열인 '{hint}'와 경로가 일치")
    if stem in request_tokens or stem in path_tokens.intersection(set(request_tokens)):
        score += 4
        rationale.append(f"파일명 '{stem}'이 요청과 직접 일치")
    ui_request = _is_ui_request(request_tokens)
    nav_request = _is_navigation_request(request_tokens)
    map_kind = None
    if ui_request and is_frontend and any(
        tok in path_tokens
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
            if nav_request:
                score -= 4
                rationale.append(
                    "탭/메뉴 배치 요청인데 core/logic 파일이라 우선순위를 낮춤"
                )
            else:
                score += 2
                rationale.append("Project Map 에서 core/logic 모듈로 분류된 파일임")
        if rel_path in project_map.large_files:
            score += 1
            rationale.append(
                "Project Map 에서 큰 파일로 표시되어 수정 후보로 우선 검토함"
            )
    if nav_request:
        if project_map is not None and rel_path in project_map.entry_files:
            score += 10
            rationale.append("탑/메뉴 이동 요청이라 entry file 이 우선 후보임")
        if any(token in path_tokens for token in _NAVIGATION_FILE_HINTS):
            score += 8
            rationale.append("탑/메뉴 구조를 가진 파일이라 목적지 후보로 적합함")
        if any(token in path_tokens for token in _CHROME_FILE_HINTS):
            score -= 16
            rationale.append(
                "탭 이동 요청인데 창 chrome/title bar 파일이라 우선순위를 낮춤"
            )
        if "/pages/" in pt or pt.startswith("pages/"):
            if stem in request_tokens:
                score -= 6
                rationale.append(
                    "탭/메뉴 요청인데 페이지 콘텐츠 파일이라 탭 컨테이너보다 우선순위를 낮춤"
                )
        if "nav-tabs" in pt or "navtabs" in path_tokens:
            score += 8
            rationale.append(
                "탭 네비게이션 영역을 직접 포함한 파일이라 목적지 후보로 적합함"
            )
        if any(token in path_tokens for token in _BACKEND_CHECKPOINT_HINTS):
            score -= 20
            rationale.append(
                "탑/메뉴 요청인데 백엔드 체크포인트 파일이라 목적지 후보에서 제외"
            )
        if "/commands/" in pt or any(
            token in path_tokens for token in _COMMAND_FILE_HINTS
        ):
            score -= 10
            rationale.append(
                "탭/메뉴 배치 요청인데 명령 처리 파일이라 UI 배치 후보에서 제외"
            )
        if map_kind == "ui" and not any(
            token in path_tokens for token in _NAVIGATION_FILE_HINTS
        ):
            score -= 2
            rationale.append("탑/메뉴 요청인데 콘텐츠형 UI 파일이라 우선순위를 낮춤")
    if any(
        tok in path_tokens
        for tok in ["worker", "service", "window", "scheduler", "backup"]
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
        file_anchors = (
            set(anchor_meta.get("anchors", []))
            if isinstance(anchor_meta, dict)
            else set()
        )
        for anchor_name, meta_entry in intent_meta.items():
            if file_anchors and anchor_name not in file_anchors:
                continue
            intent = meta_entry.get("intent", "").lower()
            if not intent:
                continue
            intent_tokens = _intent_tokens(intent)
            matched = _meaningful_overlap(request_tokens, intent_tokens)
            if matched:
                score += len(matched) * 3
                rationale.append(
                    f"앵커 intent에 키워드 '{', '.join(matched)}'이 포함됨"
                )
                break
    return score, rationale


_UI_STYLE_TOKENS = {
    "색상",
    "주황색",
    "파란색",
    "빨간색",
    "초록색",
    "노란색",
    "보라색",
    "폰트",
    "스타일",
    "디자인",
    "크기",
    "굵기",
    "투명도",
    "배경색",
    "글자색",
    "컬러",
    "사이즈",
    "보색",
}
_LOGIC_INTENT_TOKENS = {
    "번역",
    "api",
    "번역문",
    "번역기",
    "변환",
    "처리",
    "관리",
    "요청",
    "응답",
    "저장",
    "로드",
}


def _has_style_token(request_tokens: Iterable[str]) -> bool:
    """조사가 붙은 토큰도 포함해서 스타일 키워드 존재 여부 확인"""
    return any(style in tok for tok in request_tokens for style in _UI_STYLE_TOKENS)


def choose_anchor(
    anchors: list[str],
    request_tokens: list[str],
    anchor_meta: Optional[dict[str, dict[str, Any]]] = None,
) -> tuple[str, list[str]]:
    if not anchors:
        return "[먼저 앵커를 추가하세요]", ["이 파일에는 아직 앵커가 없습니다"]
    is_style_request = _has_style_token(request_tokens)
    best_anchor = anchors[0]
    best_score = -1
    best_rationale = [f"첫 번째 앵커 '{best_anchor}'를 기본값으로 선택"]
    for anchor in anchors:
        score = 0
        rationale = []
        anchor_tokens = _path_tokens(anchor)
        for token in _meaningful_overlap(request_tokens, anchor_tokens):
            score += 3
            rationale.append(f"앵커에 키워드 '{token}'이 포함됨")
        score -= _anchor_quality_penalty(anchor_tokens)
        if any(token in anchor_tokens for token in ["core", "logic", "worker"]):
            score += 1
        # intent 정보가 있으면 자연어 매칭 점수 추가
        if anchor_meta and anchor in anchor_meta:
            meta = anchor_meta[anchor]
            intent = meta.get("intent", "").lower()
            if intent:
                intent_tokens = _intent_tokens(intent)
                for token in _meaningful_overlap(request_tokens, intent_tokens):
                    score += 4
                    rationale.append(
                        f"앵커 의도('{intent[:30]}...')에 키워드 '{token}'이 포함됨"
                        if len(intent) > 30
                        else f"앵커 의도('{intent}')에 키워드 '{token}'이 포함됨"
                    )
                # 스타일 요청인데 intent가 로직 성격이면 페널티
                if is_style_request and any(
                    t in intent_tokens for t in _LOGIC_INTENT_TOKENS
                ):
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


def choose_suggested_anchor(
    suggested_anchors: list[str], request_tokens: list[str]
) -> tuple[Optional[str], list[str]]:
    if not suggested_anchors:
        return None, []
    best_anchor = suggested_anchors[0]
    best_score = -1
    best_rationale = [f"추천 앵커 '{best_anchor}'를 기본값으로 선택"]
    for anchor in suggested_anchors:
        score = 0
        rationale = []
        anchor_tokens = _path_tokens(anchor)
        matches = _meaningful_overlap(request_tokens, anchor_tokens)
        match_count = len(matches)
        for token in matches:
            score += 3
            rationale.append(f"추천 앵커에 키워드 '{token}'이 포함됨")
        if anchor.startswith("_"):
            score -= 2
            rationale.append("내부 helper 성격 이름이라 우선순위 낮춤")
        if any(
            part in anchor_tokens
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


def load_anchor_metadata(root: Path) -> dict[str, dict[str, list[str]]]:
    meta = MetaPaths(root)
    if not meta.anchor_index_path.exists():
        return {}
    try:
        payload = json.loads(meta.anchor_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    files = payload.get("files", {})
    return files if isinstance(files, dict) else {}


def _ai_select_file(
    request: str,
    candidates: list,
    root: Path,
    request_tokens: list[str],
    anchor_meta: dict,
    project_map: Optional[Any] = None,
) -> Optional[tuple]:
    """confidence가 낮을 때 AI에게 후보 파일 중 최적 파일을 선택하게 한다.

    키워드 기반 상위 후보 + ui_modules 전체를 AI에 노출해 keyword mismatch를 보완한다.
    """
    try:
        ai_explain = importlib.import_module("vibelign.core.ai_explain")
        if not ai_explain.has_ai_provider():
            return None

        # 후보 풀 구성: 상위 점수 파일 10개 + ui_modules (중복 제거)
        pool: list[Path] = [path for (_, path, _) in candidates[:10]]
        if project_map is not None:
            for rel in getattr(project_map, "ui_modules", set()):
                p = root / rel
                if p not in pool and p.exists():
                    pool.append(p)

        lines = []
        for i, path in enumerate(pool, 1):
            rel = relpath_str(root, path)
            anchors = extract_anchors(path)
            anchor_names = ", ".join(anchors[:5]) if anchors else "없음"
            try:
                content_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                snippet = "\n".join(content_lines[:20])
            except OSError:
                snippet = ""
            lines.append(
                f"{i}. {rel}\n   앵커: {anchor_names}\n   내용:\n{snippet}\n"
            )

        candidates_text = "\n---\n".join(lines)
        prompt = (
            f"사용자 코드 수정 요청: {request}\n\n"
            f"아래 후보 파일의 내용을 보고 수정해야 할 파일을 하나만 골라주세요.\n"
            f"JSON만 출력하세요. 설명 없이 딱 JSON만.\n\n"
            f"후보:\n{candidates_text}\n"
            f'출력 형식: {{"index": 1}}'
        )
        text, _ = ai_explain.generate_text_with_ai(prompt, quiet=True)
        if not text:
            return None
        m = re.search(r'"index"\s*:\s*(\d+)', text)
        if not m:
            return None
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(pool):
            selected_path = pool[idx]
            return selected_path, ["AI가 파일 내용을 분석해 가장 적합한 파일을 선택함"]
        return None
    except Exception:
        return None


def suggest_patch(root: Path, request: str, use_ai: bool = True) -> PatchSuggestion:
    from vibelign.core.anchor_tools import load_anchor_meta

    request_tokens = tokenize(request)
    metadata = load_anchor_metadata(root)
    anchor_meta = load_anchor_meta(root)
    project_map, _project_map_error = load_project_map(root)
    ui_label_idx = load_ui_label_index(root)
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
        if ui_label_idx:
            ui_boost, ui_reasons = score_boost_for_ui_labels(rel, request_tokens, ui_label_idx)
            if ui_boost:
                score += ui_boost + 8  # 화면 노출 텍스트 일치는 강한 신호 (+4 기본 + 8 추가)
                rationale = rationale + ui_reasons
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
    second_score = scored[1][0] if len(scored) > 1 else None
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
    if (
        second_score is not None
        and best_score >= 4
        and (best_score - second_score) <= 1
    ):
        confidence = "low"
        reasons = reasons[:4] + [
            f"상위 후보 점수 차이가 작음 ({best_score} vs {second_score}) — 위치 확인이 더 필요함"
        ]
    if use_ai and confidence == "low":
        ai_result = _ai_select_file(
            request, scored[:5], root, request_tokens, anchor_meta, project_map
        )
        if ai_result:
            best_path, ai_reasons = ai_result
            anchors = extract_anchors(best_path)
            anchor, ar = choose_anchor(anchors, request_tokens, anchor_meta)
            reasons = ai_reasons
            confidence = "medium"
    return PatchSuggestion(
        request, relpath_str(root, best_path), anchor, confidence, reasons[:5] + ar[:3]
    )



def suggest_patch_for_role(
    root: Path, request: str, role: str, use_ai: bool = True
) -> PatchSuggestion:
    return suggest_patch(root, request, use_ai=use_ai)


def resolve_target_for_role(
    root: Path, request: str, role: str, use_ai: bool = True
) -> "Any":
    from vibelign.core import TargetResolution

    suggestion = suggest_patch(root, request, use_ai=use_ai)
    return TargetResolution.from_suggestion(
        role=role, suggestion=suggestion, source_text=request, destination_text=request
    )


# === ANCHOR: PATCH_SUGGESTER_END ===
