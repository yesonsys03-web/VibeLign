# === ANCHOR: PATCH_SUGGESTER_START ===
from pathlib import Path
import re
import json
import importlib
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Optional, Union
from collections.abc import Mapping
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import ProjectMapSnapshot, load_project_map
from vibelign.core.project_scan import iter_source_files, relpath_str
from vibelign.core.anchor_tools import AnchorMetaEntry, extract_anchors
from vibelign.core.ui_label_index import load_ui_label_index, score_boost_for_ui_labels
from vibelign.core.import_resolver import parse_local_imports

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
    "조건": ["validators", "validate", "check"],
    "검증": ["validators", "validate", "check"],
    "필수": ["validators", "validate", "check"],
    "최대": ["config", "settings", "max"],
    "최소": ["config", "settings", "min"],
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
    "메뉴": ["menu", "nav", "navigation"],
    "첫화면": ["onboarding", "screen"],
    "시작화면": ["onboarding", "screen"],
    "버전": ["version"],
    "설정": ["settings", "config"],
    "설치": ["install"],
    "안내": ["guide"],
    "가이드": ["guide"],
    "클로드": ["claude"],
    "훅": ["hook"],
    "상태": ["state", "status"],
    "유지": ["persist", "state"],
    "활성화": ["enable", "enabled"],
    "비활성화": ["disable", "disabled"],
    "프로필": ["profile"],
    "로그인": ["login"],
    "이메일": ["email"],
    "비밀번호": ["password"],
    "서버": ["server", "app"],
    "포트": ["port"],
    "사용자": ["user", "users"],
    "회원가입": ["signup", "register"],
    "조회": ["get", "query"],
    "검증": ["validate", "validators"],
    "유효성": ["validate", "validators"],
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

# Korean alias keys sorted by length desc so prefix matching is greedy.
# Used to decompose a Korean compound like '클로드훅' into ['클로드','훅']
# without adding new dictionary entries.
_KOREAN_ALIAS_KEYS = tuple(
    sorted(
        (k for k in _TOKEN_ALIASES if re.fullmatch(r"[가-힣]+", k)),
        key=len,
        reverse=True,
    )
)


def _decompose_korean_compound(token: str) -> list[str]:
    """Greedy prefix match against known Korean alias keys.

    Returns the decomposition ONLY when the entire token is covered by
    alias keys AND at least two parts are found. This means we never
    invent a new mapping — we just recognize that a compound is made of
    parts we already know.
    """
    if not re.fullmatch(r"[가-힣]+", token):
        return []
    if token in _TOKEN_ALIASES:
        return []  # already a known key, nothing to split
    parts: list[str] = []
    i = 0
    n = len(token)
    while i < n:
        matched_key = ""
        for key in _KOREAN_ALIAS_KEYS:
            if token.startswith(key, i):
                matched_key = key
                break
        if not matched_key:
            return []
        parts.append(matched_key)
        i += len(matched_key)
    return parts if len(parts) >= 2 else []


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
        # Structurally decompose Korean compounds (e.g. '클로드훅' →
        # '클로드' + '훅') using only existing alias keys. This relays
        # the aliases of each recognized part without hand-coding the
        # compound itself.
        for part in _decompose_korean_compound(candidate):
            expanded.append(part)
            expanded.extend(_TOKEN_ALIASES.get(part, []))
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


_PASCAL_SPLIT_RE1 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_PASCAL_SPLIT_RE2 = re.compile(r"([a-z0-9])([A-Z])")


def _snake_ify_path(text: str) -> str:
    """Insert underscores at camelCase/PascalCase boundaries so downstream
    tokenizers can split 'ClaudeHookCard' into ['claude', 'hook', 'card'].
    Paths that are already lowercase or snake_case pass through unchanged.
    """
    return _PASCAL_SPLIT_RE2.sub(r"\1_\2", _PASCAL_SPLIT_RE1.sub(r"\1_\2", text))


def _path_tokens(path: Union[Path, str]) -> set[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9]+|[가-힣]+", _snake_ify_path(str(path)).lower())
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
    rationale: list[str] = []
    request_cluster = _classify_request_verb(request_tokens)
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
        anchor_cluster = _classify_anchor_verb(anchor)
        verb_delta, verb_reason = _verb_cluster_bonus(request_cluster, anchor_cluster)
        if verb_delta:
            local_score += verb_delta
        if local_score > 0:
            score = max(score, local_score)
            joined = ", ".join(dict.fromkeys(local_matches))
            rationale_line = f"{label} '{anchor}'에 키워드 {joined} 이(가) 포함됨"
            if verb_reason and verb_delta > 0:
                rationale_line += f" · {verb_reason}"
            rationale = [rationale_line]
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

_STATEFUL_UI_REQUEST_KEYWORDS = {
    "state",
    "status",
    "persist",
    "remember",
    "enable",
    "enabled",
    "disable",
    "disabled",
    "상태",
    "유지",
    "보존",
    "활성화",
    "비활성화",
}

_STATE_OWNER_FILE_HINTS = {
    "card",
    "hook",
    "toggle",
    "state",
    "status",
    "settings",
    "provider",
    "store",
    "context",
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


def _is_stateful_ui_request(request_tokens: Iterable[str]) -> bool:
    token_set = set(request_tokens)
    return any(kw in token_set for kw in _STATEFUL_UI_REQUEST_KEYWORDS)


def score_path(
    path: Path,
    request_tokens: list[str],
    rel_path: str,
    anchor_meta: Optional[dict[str, list[str]]] = None,
    project_map: Optional[ProjectMapSnapshot] = None,
    intent_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
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
    stateful_ui_request = _is_stateful_ui_request(request_tokens)
    map_kind = None
    if (
        ui_request
        and is_frontend
        and any(
            tok in path_tokens
            for tok in [
                "ui",
                "window",
                "dialog",
                "widget",
                "render",
                "terminal",
                "panel",
            ]
        )
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
        if (
            stateful_ui_request
            and nav_request
            and map_kind in {"logic", "core", "service"}
        ):
            score -= 10
            rationale.append(
                "UI 상태 유지 요청인데 backend/core/service 파일이라 우선순위를 크게 낮춤"
            )
        if rel_path in project_map.large_files:
            score += 1
            rationale.append(
                "Project Map 에서 큰 파일로 표시되어 수정 후보로 우선 검토함"
            )
    if nav_request:
        if project_map is not None and rel_path in project_map.entry_files:
            delta = 4 if stateful_ui_request else 10
            score += delta
            rationale.append(
                "상태 유지 요청이 섞여 있어 entry file 가산점을 낮춤"
                if stateful_ui_request
                else "탑/메뉴 이동 요청이라 entry file 이 우선 후보임"
            )
        if stem in {"app", "layout"}:
            delta = -3 if stateful_ui_request else 6
            score += delta
            rationale.append(
                "상태 유지 요청이라 app/layout 같은 일반 컨테이너 우선순위를 낮춤"
                if stateful_ui_request
                else "탑/메뉴 이동 요청이라 app/layout 컨테이너 파일을 우선 후보로 올림"
            )
        if any(token in path_tokens for token in _NAVIGATION_FILE_HINTS):
            delta = 2 if stateful_ui_request else 8
            score += delta
            rationale.append(
                "상태 유지 요청이라 메뉴 컨테이너 가산점을 낮춤"
                if stateful_ui_request
                else "탑/메뉴 구조를 가진 파일이라 목적지 후보로 적합함"
            )
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
        if (
            map_kind == "ui"
            and not stateful_ui_request
            and not any(token in path_tokens for token in _NAVIGATION_FILE_HINTS)
        ):
            score -= 2
            rationale.append("탑/메뉴 요청인데 콘텐츠형 UI 파일이라 우선순위를 낮춤")
    if (
        stateful_ui_request
        and is_frontend
        and any(token in path_tokens for token in _STATE_OWNER_FILE_HINTS)
    ):
        score += 8
        rationale.append("상태 유지 요청이라 카드/상태 소유자 후보 파일을 우선 검토함")
    if stateful_ui_request and nav_request and is_frontend:
        score += 6
        rationale.append(
            "메뉴 이동 뒤 UI 상태 유지 요청이라 프론트엔드 파일을 우선 검토함"
        )
    if stateful_ui_request and any(
        token in path_tokens for token in {"card", "component", "components"}
    ):
        score += 6
        rationale.append("상태 유지 요청이라 카드/컴포넌트 파일 우선순위를 올림")
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
        request_cluster = _classify_request_verb(request_tokens)
        best_delta = 0
        best_anchor_name: Optional[str] = None
        best_matched: list[str] = []
        best_verb_reason: Optional[str] = None
        best_verb_delta = 0
        for anchor_name, meta_entry in intent_meta.items():
            if file_anchors and anchor_name not in file_anchors:
                continue
            intent = meta_entry.get("intent", "").lower()
            if not intent:
                continue
            intent_tokens = _intent_tokens(intent)
            matched = _meaningful_overlap(request_tokens, intent_tokens)
            if not matched:
                continue
            kw_delta = len(matched) * 3
            anchor_cluster = _classify_anchor_verb(anchor_name)
            intent_cluster = _classify_intent_verb(intent)
            effective_cluster = anchor_cluster or intent_cluster
            verb_delta, verb_reason = _verb_cluster_bonus(
                request_cluster, effective_cluster
            )
            total_delta = kw_delta + verb_delta
            if total_delta > best_delta:
                best_delta = total_delta
                best_anchor_name = anchor_name
                best_matched = matched
                best_verb_reason = verb_reason
                best_verb_delta = verb_delta
        if best_anchor_name is not None:
            score += best_delta
            rationale.append(
                f"앵커 intent에 키워드 '{', '.join(best_matched)}'이 포함됨"
            )
            if best_verb_reason and best_verb_delta > 0:
                rationale.append(f"intent 동사 일치: {best_verb_reason}")
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

# --- Verb cluster classification (C1 — F1/F3 fix) ---
_VERB_CLUSTER_MUTATE = "MUTATE"
_VERB_CLUSTER_CREATE = "CREATE"
_VERB_CLUSTER_DELETE = "DELETE"
_VERB_CLUSTER_READ = "READ"

# Request-side verb tokens (Korean stems + English). Tokens compared against
# the output of `tokenize(request)`, which lowercases and strips Korean
# particles. Prefix match (startswith) is used so that inflected forms like
# "바꿔" / "바꿔줘" / "바꿨" all map through a single stem.
_REQUEST_VERB_STEMS: tuple[tuple[str, str], ...] = (
    # MUTATE — modify existing state
    ("바꿔", _VERB_CLUSTER_MUTATE),
    ("바꾸", _VERB_CLUSTER_MUTATE),
    ("변경", _VERB_CLUSTER_MUTATE),
    ("수정", _VERB_CLUSTER_MUTATE),
    ("고쳐", _VERB_CLUSTER_MUTATE),
    ("고치", _VERB_CLUSTER_MUTATE),
    ("버그", _VERB_CLUSTER_MUTATE),
    ("갱신", _VERB_CLUSTER_MUTATE),
    ("업데이트", _VERB_CLUSTER_MUTATE),
    ("update", _VERB_CLUSTER_MUTATE),
    ("change", _VERB_CLUSTER_MUTATE),
    ("fix", _VERB_CLUSTER_MUTATE),
    ("modify", _VERB_CLUSTER_MUTATE),
    ("set", _VERB_CLUSTER_MUTATE),
    # CREATE — add new behavior/state
    ("추가", _VERB_CLUSTER_CREATE),
    ("생성", _VERB_CLUSTER_CREATE),
    ("만들", _VERB_CLUSTER_CREATE),
    ("신규", _VERB_CLUSTER_CREATE),
    ("add", _VERB_CLUSTER_CREATE),
    ("create", _VERB_CLUSTER_CREATE),
    ("new", _VERB_CLUSTER_CREATE),
    ("register", _VERB_CLUSTER_CREATE),
    # DELETE — remove existing behavior/state
    ("삭제", _VERB_CLUSTER_DELETE),
    ("제거", _VERB_CLUSTER_DELETE),
    ("없애", _VERB_CLUSTER_DELETE),
    ("지워", _VERB_CLUSTER_DELETE),
    ("delete", _VERB_CLUSTER_DELETE),
    ("remove", _VERB_CLUSTER_DELETE),
    ("drop", _VERB_CLUSTER_DELETE),
    # READ — display or retrieve without modifying
    ("보여", _VERB_CLUSTER_READ),
    ("조회", _VERB_CLUSTER_READ),
    ("표시", _VERB_CLUSTER_READ),
    ("출력", _VERB_CLUSTER_READ),
    ("show", _VERB_CLUSTER_READ),
    ("display", _VERB_CLUSTER_READ),
    ("render", _VERB_CLUSTER_READ),
    ("get", _VERB_CLUSTER_READ),
    ("read", _VERB_CLUSTER_READ),
    ("list", _VERB_CLUSTER_READ),
    ("view", _VERB_CLUSTER_READ),
)

# Anchor-name token → cluster. Anchor names are ALL_CAPS snake case; we
# lowercase them and match tokens against the keys below.
_ANCHOR_VERB_TOKENS: dict[str, str] = {
    "handle": _VERB_CLUSTER_MUTATE,
    "update": _VERB_CLUSTER_MUTATE,
    "set": _VERB_CLUSTER_MUTATE,
    "write": _VERB_CLUSTER_MUTATE,
    "save": _VERB_CLUSTER_MUTATE,
    "patch": _VERB_CLUSTER_MUTATE,
    "edit": _VERB_CLUSTER_MUTATE,
    "modify": _VERB_CLUSTER_MUTATE,
    "process": _VERB_CLUSTER_MUTATE,
    "submit": _VERB_CLUSTER_MUTATE,
    "create": _VERB_CLUSTER_CREATE,
    "add": _VERB_CLUSTER_CREATE,
    "insert": _VERB_CLUSTER_CREATE,
    "register": _VERB_CLUSTER_CREATE,
    "new": _VERB_CLUSTER_CREATE,
    "delete": _VERB_CLUSTER_DELETE,
    "remove": _VERB_CLUSTER_DELETE,
    "drop": _VERB_CLUSTER_DELETE,
    "clear": _VERB_CLUSTER_DELETE,
    "get": _VERB_CLUSTER_READ,
    "read": _VERB_CLUSTER_READ,
    "load": _VERB_CLUSTER_READ,
    "fetch": _VERB_CLUSTER_READ,
    "find": _VERB_CLUSTER_READ,
    "list": _VERB_CLUSTER_READ,
    "render": _VERB_CLUSTER_READ,
    "show": _VERB_CLUSTER_READ,
    "display": _VERB_CLUSTER_READ,
    "view": _VERB_CLUSTER_READ,
    "validate": _VERB_CLUSTER_READ,
    "check": _VERB_CLUSTER_READ,
}


def _classify_request_verb(request_tokens: Iterable[str]) -> Optional[str]:
    """Return the verb cluster implied by a tokenized request, or None.

    Scans each request token and returns the cluster of the LAST matching
    stem. Korean places the main action verb at the end of the sentence, so
    the last match reflects the dominant intent (e.g. "비밀번호 변경 기능 추가"
    has both MUTATE("변경") and CREATE("추가"); "추가" wins as the final verb).
    """
    token_list = list(request_tokens)
    last_cluster: Optional[str] = None
    for token in token_list:
        for stem, cluster in _REQUEST_VERB_STEMS:
            if token.startswith(stem):
                last_cluster = cluster
                break
    return last_cluster


def _classify_anchor_verb(anchor_name: str) -> Optional[str]:
    """Return the verb cluster implied by an anchor name, or None.

    Splits the anchor name on underscores and looks up each token in
    _ANCHOR_VERB_TOKENS. Returns the cluster of the LAST verb token found,
    because anchor naming convention places the verb after the module/object
    prefix (e.g. LOGIN_HANDLE_LOGIN → HANDLE, PROFILE_HANDLE_PROFILE_UPDATE
    → UPDATE). Later tokens describe the specific operation.
    """
    if not anchor_name:
        return None
    last_cluster: Optional[str] = None
    for part in anchor_name.lower().split("_"):
        cluster = _ANCHOR_VERB_TOKENS.get(part)
        if cluster is not None:
            last_cluster = cluster
    return last_cluster


def _classify_intent_verb(intent_text: str) -> Optional[str]:
    """Return the verb cluster implied by an anchor intent string, or None.

    Collects every matching stem across the intent's tokens and returns
    the LAST match, consistent with `_classify_request_verb`. `_intent_tokens`
    returns a set, so we scan all tokens rather than short-circuiting on the
    first hit — that way the result is invariant under Python's hash-seed
    randomization.

    Falls back to a substring scan for Korean verbs like "처리합니다" /
    "저장됩니다" where the stem is fused with the inflection and the
    tokenizer would not surface it as a separate token.
    """
    if not intent_text:
        return None
    last_cluster: Optional[str] = None
    for token in _intent_tokens(intent_text):
        for stem, cluster in _REQUEST_VERB_STEMS:
            if token.startswith(stem):
                last_cluster = cluster
                break
    if last_cluster is not None:
        return last_cluster
    lowered = intent_text.lower()
    processing_stems = (
        ("처리", _VERB_CLUSTER_MUTATE),
        ("저장", _VERB_CLUSTER_MUTATE),
    )
    for stem, cluster in processing_stems:
        if stem in lowered:
            return cluster
    return None


def _verb_cluster_bonus(
    request_cluster: Optional[str],
    anchor_cluster: Optional[str],
) -> tuple[int, Optional[str]]:
    """Return (score_delta, rationale_text_or_None) for a single comparison.

    Match: +5. Mismatch: −4. The mismatch penalty is heavier than the plan's
    initial −2 because intent descriptions that restate request wording can
    pile up +20 in keyword overlap on the wrong-verb sibling, which a smaller
    penalty cannot overcome. See ChooseAnchorVerbPreferenceTest F1 regression.
    """
    if request_cluster is None or anchor_cluster is None:
        return 0, None
    if request_cluster == anchor_cluster:
        return 5, f"요청 동사 클러스터({request_cluster})가 앵커와 일치"
    return -4, f"요청 동사 클러스터({request_cluster}) ↔ 앵커({anchor_cluster}) 불일치"


def _has_style_token(request_tokens: Iterable[str]) -> bool:
    """조사가 붙은 토큰도 포함해서 스타일 키워드 존재 여부 확인"""
    return any(style in tok for tok in request_tokens for style in _UI_STYLE_TOKENS)


_UI_ELEMENT_TOKENS = {
    "폼", "버튼", "텍스트", "placeholder", "필드", "라벨",
    "label", "field", "form", "button", "input", "title",
    "submit", "체크박스", "셀렉트", "드롭다운", "아이콘",
}
_RENDER_ANCHOR_TOKENS = {"render", "show", "display", "view", "form"}
_UI_ELEMENT_RENDER_BONUS = 6

_WRAPPER_ANCHOR_PENALTY = 5


def _is_wrapper_anchor(anchor: str, all_anchors: list[str]) -> bool:
    if len(all_anchors) < 2:
        return False
    tokens = _path_tokens(anchor)
    if len(tokens) != 1:
        return False
    token = next(iter(tokens))
    return all(
        token in _path_tokens(other)
        for other in all_anchors
        if other != anchor
    )


def choose_anchor(
    anchors: list[str],
    request_tokens: list[str],
    anchor_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> tuple[str, list[str]]:
    if not anchors:
        return "[먼저 앵커를 추가하세요]", ["이 파일에는 아직 앵커가 없습니다"]
    is_style_request = _has_style_token(request_tokens)
    is_ui_element_request = any(
        ui in tok for tok in request_tokens for ui in _UI_ELEMENT_TOKENS
    )
    raw_verb_cluster = _classify_request_verb(request_tokens)
    ui_element_verb_override = (
        is_ui_element_request and raw_verb_cluster != _VERB_CLUSTER_DELETE
    )
    request_verb_cluster = None if ui_element_verb_override else raw_verb_cluster
    best_anchor = anchors[0]
    best_score = float("-inf")
    best_rationale = [f"첫 번째 앵커 '{best_anchor}'를 기본값으로 선택"]
    for anchor in anchors:
        score = 0
        rationale = []
        anchor_tokens = _path_tokens(anchor)
        for token in _meaningful_overlap(request_tokens, anchor_tokens):
            score += 3
            rationale.append(f"앵커에 키워드 '{token}'이 포함됨")
        score -= _anchor_quality_penalty(anchor_tokens)
        if _is_wrapper_anchor(anchor, anchors):
            score -= _WRAPPER_ANCHOR_PENALTY
            rationale.append("파일 전체를 감싸는 wrapper 앵커라 우선순위 낮춤")
        if any(token in anchor_tokens for token in ["core", "logic", "worker"]):
            score += 1
        name_cluster = _classify_anchor_verb(anchor)
        name_delta, name_reason = _verb_cluster_bonus(
            request_verb_cluster, name_cluster
        )
        is_render_anchor = any(t in anchor_tokens for t in _RENDER_ANCHOR_TOKENS)
        ui_render_applicable = is_ui_element_request and is_render_anchor and ui_element_verb_override
        if name_delta:
            score += name_delta
            if name_reason:
                rationale.append(name_reason)
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
                intent_cluster = _classify_intent_verb(intent)
                intent_delta, intent_reason = _verb_cluster_bonus(
                    request_verb_cluster, intent_cluster
                )
                if intent_delta:
                    score += intent_delta
                    if intent_reason:
                        rationale.append(f"의도 동사: {intent_reason}")
                # 스타일 요청인데 intent가 로직 성격이면 페널티
                if is_style_request and any(
                    t in intent_tokens for t in _LOGIC_INTENT_TOKENS
                ):
                    score -= 5
                    rationale.append("스타일 요청인데 로직 성격 앵커라 우선순위 낮춤")
            warning = meta.get("warning")
            if warning:
                rationale.append(f"⚠️ {warning}")
        if ui_render_applicable:
            score += _UI_ELEMENT_RENDER_BONUS
            rationale.append("UI 요소 변경 요청이라 render 앵커 우선")
        if raw_verb_cluster == _VERB_CLUSTER_DELETE and is_render_anchor:
            score -= 2
            rationale.append("삭제 요청이라 render 앵커 우선순위 낮춤")
        if score > best_score or (score == best_score and score < 0):
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


# === ANCHOR: PATCH_SUGGESTER__BUILD_IMPORT_POOL_EXPANSION_START ===
def _build_import_pool_expansion(
    top_candidate: Path, root: Path, max_hops: int = 1
) -> list[Path]:
    """top_candidate 파일의 로컬 import를 최대 max_hops 깊이까지 탐색해 반환한다.

    wrapper 컴포넌트가 top candidate일 때, import된 실제 상태 소유 파일을
    AI 후보 풀에 추가하기 위해 사용된다.
    """
    visited: set[Path] = {top_candidate}
    frontier: list[Path] = [top_candidate]
    result: list[Path] = []
    for _ in range(max_hops):
        next_frontier: list[Path] = []
        for f in frontier:
            for imported in parse_local_imports(f, root):
                if imported not in visited:
                    visited.add(imported)
                    next_frontier.append(imported)
                    result.append(imported)
        frontier = next_frontier
    return result
# === ANCHOR: PATCH_SUGGESTER__BUILD_IMPORT_POOL_EXPANSION_END ===


def _ai_select_file(
    request: str,
    candidates: list[tuple[int, Path, list[str]]],
    root: Path,
    request_tokens: list[str],
    anchor_meta: Mapping[str, Mapping[str, Any]],
    project_map: Optional[Any] = None,
) -> tuple[Path, list[str]] | None:
    """confidence가 낮을 때 AI에게 후보 파일 중 최적 파일을 선택하게 한다.

    키워드 기반 상위 후보 + ui_modules 전체를 AI에 노출해 keyword mismatch를 보완한다.
    """
    try:
        ai_explain = importlib.import_module("vibelign.core.ai_explain")
        if not ai_explain.has_ai_provider():
            return None
        stateful_ui_request = _is_stateful_ui_request(request_tokens)

        # 후보 풀 구성: 상위 점수 파일 10개 + ui_modules (중복 제거)
        pool: list[Path] = [path for (_, path, _) in candidates[:10]]
        if project_map is not None:
            for rel in getattr(project_map, "ui_modules", set()):
                p = root / rel
                if p not in pool and p.exists():
                    pool.append(p)
        # top candidate의 import를 1-hop 탐색해 풀에 추가 (wrapper → 실제 상태 소유 파일)
        if candidates:
            top_path = candidates[0][1]
            for imported in _build_import_pool_expansion(top_path, root, max_hops=1):
                if imported not in pool:
                    pool.append(imported)

        # 파일 수에 따라 스니펫 줄 수 조정 (프롬프트 과부하 방지)
        snippet_lines = max(5, 30 // max(len(pool), 1))

        lines: list[str] = []
        for i, path in enumerate(pool, 1):
            rel = relpath_str(root, path)
            anchors = extract_anchors(path)
            anchor_names = ", ".join(anchors[:5]) if anchors else "없음"
            try:
                content_lines = path.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()
                snippet = "\n".join(content_lines[:snippet_lines])
            except OSError:
                snippet = ""
            lines.append(f"{i}. {rel}\n   앵커: {anchor_names}\n   내용:\n{snippet}\n")

        candidates_text = "\n---\n".join(lines)
        prompt = (
            f"사용자 코드 수정 요청: {request}\n\n"
            f"아래 후보 파일의 내용을 보고 수정해야 할 파일을 하나만 골라주세요.\n"
            f"JSON만 출력하세요. 설명 없이 딱 JSON만.\n\n"
            f"{('중요 규칙: 상태 유지/enable/disable/status 문제가 메뉴 이동 뒤에 풀리는 요청이면, 일반적인 app/layout 컨테이너보다 실제 상태를 들고 있거나 카드/토글/설정/훅 이름이 보이는 파일을 우선 고르세요.\\n\\n' if stateful_ui_request else '')}"
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


# --- C2 layer routing post-processing ---
#
# After C1 verb-aware scoring ranks files, promote a ui-layer caller over
# a non-ui top1 when the request is a CREATE-style request and the caller
# imports the top1. The four gates protect existing correct routings from
# regressing. See docs/superpowers/specs/2026-04-12-patch-accuracy-c2-
# layer-routing-design.md for the full rationale; tune values only with
# measurement data.
_LAYER_ROUTING_BOOST = 18
_LAYER_ROUTING_PENALTY = 3


def _apply_layer_routing(
    candidates: list[tuple[Path, int]],
    request_tokens: list[str],
    project_map: Optional[ProjectMapSnapshot],
    root: Path,
) -> list[tuple[Path, int]]:
    """Promote a ui-layer caller when the top1 is a non-ui file that the
    caller imports, the request is a CREATE verb, and the caller already
    has a positive base score. See spec §3 for gate definitions.

    Returns the rewritten candidate list sorted descending by score.
    Returns the input unchanged when any gate fails or when project_map
    is None.
    """
    if not candidates or project_map is None:
        return candidates

    top_path, _top_score = candidates[0]
    top_rel = relpath_str(root, top_path)

    # Gate 1: top1 must NOT already be a ui file.
    if project_map.classify_path(top_rel) == "ui":
        return candidates

    # Gate 2: request verb cluster must be CREATE.
    verb_cluster = _classify_request_verb(request_tokens)
    if verb_cluster != _VERB_CLUSTER_CREATE:
        return candidates

    # Gate 3: top1 must have at least one ui-layer importer.
    file_entry = project_map.files.get(top_rel, {})
    raw_importers = file_entry.get("imported_by", [])
    if not isinstance(raw_importers, list):
        return candidates
    ui_importers = [
        rel for rel in raw_importers
        if isinstance(rel, str) and project_map.classify_path(rel) == "ui"
    ]
    if not ui_importers:
        return candidates

    # Gate 4: at least one ui importer must have score > 0 in candidates.
    candidate_by_rel: dict[str, tuple[Path, int]] = {
        relpath_str(root, p): (p, s) for p, s in candidates
    }
    positive_callers = [
        (rel, *candidate_by_rel[rel])
        for rel in ui_importers
        if rel in candidate_by_rel and candidate_by_rel[rel][1] > 0
    ]
    if not positive_callers:
        return candidates

    # Pick the highest-scoring positive ui caller.
    positive_callers.sort(key=lambda item: item[2], reverse=True)
    _, best_path, _ = positive_callers[0]

    new_candidates: list[tuple[Path, int]] = []
    for path, score in candidates:
        if path == best_path:
            new_candidates.append((path, score + _LAYER_ROUTING_BOOST))
        elif path == top_path:
            new_candidates.append((path, score - _LAYER_ROUTING_PENALTY))
        else:
            new_candidates.append((path, score))
    new_candidates.sort(key=lambda item: (-item[1], str(item[0])))
    return new_candidates


def _score_all_files(
    root: Path, request: str
) -> tuple[
    list[tuple[int, Path, list[str]]],
    dict[str, dict[str, list[str]]],
    dict[str, AnchorMetaEntry],
    ProjectMapSnapshot | None,
    dict[str, list[dict[str, int | str]]],
]:
    """Rank every source file under `root` for the given `request`.

    Returns (scored, metadata, anchor_meta, project_map, ui_label_idx).
    `scored` is sorted descending by score, ties broken by path string.
    `suggest_patch` consumes all 5 return values; `score_candidates`
    consumes only `scored`.
    """
    from vibelign.core.anchor_tools import load_anchor_meta

    request_tokens = tokenize(request)
    metadata = load_anchor_metadata(root)
    anchor_meta = load_anchor_meta(root)
    project_map, _err = load_project_map(root)
    ui_label_idx = load_ui_label_index(root)
    scored: list[tuple[int, Path, list[str]]] = []
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
            ui_boost, ui_reasons = score_boost_for_ui_labels(
                rel, request_tokens, ui_label_idx
            )
            if ui_boost:
                score += ui_boost + 8
                rationale = rationale + ui_reasons
        scored.append((score, path, rationale))
    scored.sort(key=lambda x: (-x[0], str(x[1])))

    # C2 layer routing post-processing. See _apply_layer_routing docstring.
    candidates = [(path, score) for score, path, _ in scored]
    rewritten = _apply_layer_routing(candidates, request_tokens, project_map, root)
    if rewritten != candidates:
        rationale_by_path = {path: rationale for _, path, rationale in scored}
        scored = [
            (score, path, rationale_by_path[path] + ["C2 레이어 라우팅 재배치"])
            for path, score in rewritten
        ]
    return scored, metadata, anchor_meta, project_map, ui_label_idx


def score_candidates(root: Path, request: str) -> list[tuple[Path, int]]:
    """Public API: return files ranked for `request`, descending by score.

    Used by the patch-accuracy benchmark runner to measure prefilter recall.
    This is the same ranking `suggest_patch` uses internally before the
    AI-select / anchor-pick stages — extracted so downstream tooling can
    inspect the raw deterministic order.
    """
    scored, *_ = _score_all_files(root, request)
    return [(path, score) for score, path, _rationale in scored]


def suggest_patch(root: Path, request: str, use_ai: bool = True) -> PatchSuggestion:
    scored, metadata, anchor_meta, project_map, _ui_label_idx = _score_all_files(
        root, request
    )
    request_tokens = tokenize(request)
    if not scored:
        return PatchSuggestion(
            request,
            "[소스 파일 없음]",
            "[없음]",
            "low",
            ["프로젝트에 아직 소스 파일이 없습니다"],
        )
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
    stateful_ui_request = _is_stateful_ui_request(request_tokens)
    # Deference rule (C6, 2026-04-12):
    # - confidence == "low": AI always invoked (use_ai flag irrelevant)
    # - confidence == "medium" + use_ai: AI invoked (user escape hatch)
    # - confidence == "high" + use_ai: AI **skipped** — deterministic top-1
    #   is trusted. Prevents --ai from overriding C1 verb-aware ranking on
    #   scenarios where deterministic already found the right file.
    # - use_ai=False + confidence != "low": AI not invoked (unchanged)
    best_path_tokens = _path_tokens(relpath_str(root, best_path))
    best_is_frontend = best_path.suffix.lower() in _FRONTEND_EXTS
    ai_override_blocked_by_state_hint = (
        stateful_ui_request
        and best_is_frontend
        and any(token in best_path_tokens for token in _STATE_OWNER_FILE_HINTS)
    )
    should_use_ai = confidence == "low" or (
        use_ai
        and confidence != "high"
        and not ai_override_blocked_by_state_hint
    )
    if should_use_ai:
        ai_result = _ai_select_file(
            request, scored, root, request_tokens, anchor_meta, project_map
        )
        if ai_result:
            ai_path_or_none, ai_reasons = ai_result
            if ai_path_or_none is not None:
                best_path = ai_path_or_none
                # Recover keyword-based rationale for the AI-selected file so
                # downstream callers still see WHY the file matched the request.
                original_reasons: list[str] = []
                for _s, p, r in scored:
                    if p == best_path:
                        original_reasons = r
                        break
                anchors = extract_anchors(best_path)
                anchor, ar = choose_anchor(anchors, request_tokens, anchor_meta)
                # Re-run the suggested-anchor fallback for the newly selected
                # file. Without this the anchor would revert to
                # "[먼저 앵커를 추가하세요]" even when a suggested anchor exists.
                if anchor == "[먼저 앵커를 추가하세요]":
                    file_meta = (
                        metadata.get(relpath_str(root, best_path), {})
                        if metadata
                        else {}
                    )
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
                reasons = (original_reasons[:4] if original_reasons else []) + ai_reasons
                if confidence != "low":
                    confidence = "high"  # AI가 직접 선택 시 신뢰도 유지
            else:
                reasons = reasons[:4] + ai_reasons
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
