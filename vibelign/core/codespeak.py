# === ANCHOR: CODESPEAK_START ===
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from vibelign.core.intent_ir import IntentIR


ACTION_MAP = {
    "add": [
        "add",
        "insert",
        "create",
        "append",
        "new",
        "make",
        "build",
        "추가",
        "넣어",
        "만들어",
        "생성",
        "넣기",
        "추가해",
        "만들기",
    ],
    "remove": [
        "remove",
        "delete",
        "drop",
        "clear",
        "clean",
        "삭제",
        "제거",
        "지워",
        "없애",
        "지우기",
        "삭제해",
    ],
    "move": [
        "move",
        "move to",
        "relocate",
        "transfer",
        "reposition",
        "이동",
        "옮겨",
        "옮기",
        "배치",
        "옆으로",
        "옆에",
        "붙여",
        "붙여줘",
        "배치해",
        "이관",
        "이동해",
        "옮겨줘",
    ],
    "fix": [
        "fix",
        "repair",
        "resolve",
        "debug",
        "handle",
        "catch",
        "수정",
        "고쳐",
        "해결",
        "버그",
        "고치기",
        "수정해",
        "고쳐줘",
    ],
    "update": [
        "update",
        "change",
        "edit",
        "modify",
        "improve",
        "enhance",
        "upgrade",
        "변경",
        "바꿔",
        "키워",
        "줄여",
        "수정해",
        "바꾸기",
        "변경해",
        "업데이트",
    ],
    "split": [
        "split",
        "separate",
        "divide",
        "extract",
        "refactor",
        "분리",
        "나눠",
        "쪼개",
        "추출",
        "리팩토링",
    ],
    "apply": [
        "apply",
        "set",
        "enable",
        "activate",
        "적용",
        "설정",
        "활성화",
        "켜줘",
        "적용해",
    ],
}

LAYER_MAP = {
    "ui": [
        "button",
        "window",
        "dialog",
        "layout",
        "sidebar",
        "toolbar",
        "panel",
        "screen",
        "render",
        "widget",
        "progress",
        "menu",
        "버튼",
        "화면",
        "창",
        "레이아웃",
        "메뉴",
        "패널",
        "툴바",
        "사이드바",
        "팝업",
        "모달",
        "탭",
        "아이콘",
        "폼",
        "입력",
        "목록",
        "리스트",
        "진행바",
        "진행표시",
        "체크박스",
        "체크",
        "드롭다운",
        "셀렉트",
        "슬라이더",
        "스크롤",
        "토글",
        "찾아보기",
        "선택창",
        "업로드",
        "라디오",
        "스피너",
        "배지",
        "툴팁",
        "헤더",
        "푸터",
        "네비게이션",
    ],
    "service": [
        "login",
        "auth",
        "register",
        "user",
        "session",
        "token",
        "password",
        "로그인",
        "인증",
        "회원",
        "비밀번호",
        "세션",
        "가입",
        "로그아웃",
        "사용자",
        "유저",
        "계정",
        "프로필",
    ],
    "engine": [
        "patch",
        "anchor",
        "guard",
        "scan",
        "analyze",
        "build",
        "compile",
        "앵커",
        "패치",
        "스캔",
        "분석",
        "빌드",
        "컴파일",
    ],
    "api": [
        "request",
        "fetch",
        "http",
        "endpoint",
        "route",
        "server",
        "response",
        "요청",
        "서버",
        "엔드포인트",
        "라우트",
        "응답",
        "api",
        "호출",
    ],
    "data": [
        "db",
        "database",
        "model",
        "schema",
        "store",
        "cache",
        "json",
        "yaml",
        "file",
        "save",
        "load",
        "데이터",
        "데이터베이스",
        "모델",
        "저장",
        "불러오기",
        "캐시",
        "파일",
    ],
    "cli": [
        "command",
        "arg",
        "flag",
        "option",
        "help",
        "output",
        "print",
        "명령어",
        "커맨드",
        "옵션",
        "출력",
        "도움말",
    ],
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "with",
    "and",
    "of",
    "in",
    "on",
    "please",
    "my",
    "this",
    "that",
    "me",
    "을",
    "를",
    "이",
    "가",
    "에",
    "에서",
    "으로",
    "로",
    "와",
    "과",
    "좀",
    "해줘",
    "줘",
    "해",
    "주세요",
    "부탁",
    "그",
    "저",
    "제",
    "좀더",
    "더",
    "다시",
    "한번",
    "잠깐",
    "동일하게",
    "통일",
    "같게",
    "맞춰",
    "맞춰줘",
    "통일해",
    "통일해줘",
    "달라",
    "다르게",
    "사이즈가",
    "크기가",
    "높이가",
    "너비가",
    "가로가",
    "세로가",
}

TARGET_HINTS = {
    "ui": "component",
    "service": "auth",
    "engine": "pipeline",
    "api": "endpoint",
    "data": "resource",
    "cli": "command",
    "core": "patch",
}

CODESPEAK_V0_RE = re.compile(
    r"^(?P<layer>[a-z][a-z0-9_]*)\.(?P<target>[a-z][a-z0-9_]*)\.(?P<subject>[a-z0-9가-힣][a-z0-9가-힣_]*)\.(?P<action>[a-z][a-z0-9_]*)$"
)


@dataclass
class CodeSpeakResult:
    codespeak: str
    layer: str
    target: str
    subject: str
    action: str
    confidence: str
    interpretation: str
    clarifying_questions: list[str]
    patch_points: dict[str, str]
    intent_ir: IntentIR | None = None
    target_file: str | None = None
    target_anchor: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_codespeak_v0(codespeak: str) -> dict[str, str] | None:
    match = CODESPEAK_V0_RE.fullmatch(codespeak.strip())
    if match is None:
        return None
    return match.groupdict()


def is_valid_codespeak_v0(codespeak: str) -> bool:
    return parse_codespeak_v0(codespeak) is not None


def tokenize_request(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_가-힣]+", text.lower())


def _infer_action(tokens: list[str]) -> tuple[str, int]:
    # 정확 일치 우선
    for action, words in ACTION_MAP.items():
        for token in tokens:
            if token in words:
                return action, 2
    # 한국어 복합 동사 부분 포함 검사 (예: "추가해줘" → "추가" 포함)
    for action, words in ACTION_MAP.items():
        for token in tokens:
            for word in words:
                if len(word) >= 2 and word in token:
                    return action, 1
    return "update", 0


def _extract_patch_points(request: str, action: str) -> tuple[dict[str, str], int]:
    normalized = re.sub(r"\s+", " ", request.strip())
    points = {
        "operation": action,
        "source": "",
        "destination": "",
        "object": "",
        "behavior_constraint": "",
    }
    rationale: list[str] = []

    move_patterns = [
        re.compile(
            r"^(?P<source>.+?)\s*(?:삭제하고|빼서|지우고|제거하고|없애고)\s*(?P<destination>.+?)(?:옆으로|옆에|옆으로\s*가|옆에\s*가)\s*(?:이동시켜|이동|옮겨|옮기|이관|move|relocate|붙여|배치|배치해|두|둔|둬|가는\s*게|가는게)(?:[.!?]\s*)?(?P<behavior>.*)$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(?P<source>.+?)(?:을|를|은|는)\s*(?P<destination>.+?)(?:옆으로|옆에|옆으로\s*가|옆에\s*가)\s*(?:이동시켜|가는|가는게|가는\s*것이|가는\s*것|붙여|배치|배치해|두|둬|가는\s*게)(?:[.!?]\s*)?(?P<behavior>.*)$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(?P<source>.+?)(?:을|를|은|는)\s*(?P<destination>.+?)(?:로|으로|에)\s*(?:이동시켜|이동|옮겨|옮기|이관|move|relocate)(?:[.!?]\s*)?(?P<behavior>.*)$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(?P<source>.+?)\s*(?:move|relocate|transfer)\s*(?:to|into)\s*(?P<destination>.+?)(?:[.!?]\s*)?(?P<behavior>.*)$",
            re.IGNORECASE,
        ),
    ]
    for pattern in move_patterns:
        match = pattern.search(normalized)
        if match:
            source = match.group("source").strip()
            destination = match.group("destination").strip()
            behavior = match.groupdict().get("behavior", "").strip()
            if behavior.startswith("그리고 "):
                behavior = behavior[len("그리고 ") :].strip()
            points["source"] = source
            points["destination"] = destination
            points["object"] = source
            points["behavior_constraint"] = behavior
            points["operation"] = "move"
            rationale.append("복합 이동 요청으로 읽혀 source/destination을 분리함")
            if behavior:
                rationale.append("뒤따르는 보존 조건을 별도 제약으로 분리함")
            return points, 2

    if action in {"add", "fix", "update", "apply"}:
        object_match = re.search(
            r"^(?P<object>.+?)(?:을|를|은|는)\s*(?:추가|넣어|만들|생성|수정|바꿔|변경|업데이트|적용)",
            normalized,
            re.IGNORECASE,
        )
        if object_match:
            obj = object_match.group("object").strip()
            points["source"] = obj
            points["object"] = obj
            rationale.append("수정 대상 객체를 추출함")
            return points, 1

    if action == "remove":
        remove_match = re.search(
            r"^(?P<object>.+?)(?:을|를|은|는)\s*(?:삭제|제거|지워|없애)",
            normalized,
            re.IGNORECASE,
        )
        if remove_match:
            obj = remove_match.group("object").strip()
            points["source"] = obj
            points["object"] = obj
            rationale.append("삭제 대상 객체를 추출함")
            return points, 1

    tokens = tokenize_request(request)
    candidates = [token for token in tokens if token not in STOPWORDS]
    if candidates:
        points["object"] = " ".join(candidates[:3])
    rationale.append("명시적 구조가 없어 요청 텍스트를 기준으로 보수적으로 추출함")
    return points, 0


def _infer_layer(tokens: list[str]) -> tuple[str, int]:
    # 정확 일치 우선
    for layer, words in LAYER_MAP.items():
        for token in tokens:
            if token in words:
                return layer, 2
    # 한국어 복합 어절 부분 포함 검사
    for layer, words in LAYER_MAP.items():
        for token in tokens:
            for word in words:
                if len(word) >= 2 and word in token:
                    return layer, 1
    return "core", 0


def _infer_target(tokens: list[str], layer: str) -> str:
    if layer == "ui":
        if "layout" in tokens or "sidebar" in tokens or "toolbar" in tokens:
            return "layout"
        return "component"
    if layer == "service" and "login" in tokens:
        return "auth"
    return TARGET_HINTS.get(layer, "patch")


def _infer_subject(tokens: list[str], layer: str, action: str) -> tuple[str, int]:
    excluded = set(STOPWORDS)
    excluded.add(action)
    all_action_words: set[str] = set()
    for words in ACTION_MAP.values():
        all_action_words.update(words)
    excluded.update(all_action_words)
    candidates = [
        token
        for token in tokens
        if token not in excluded
        and not any(w in token for w in all_action_words if len(w) >= 2)
    ]
    if not candidates:
        return f"{layer}_request", 0
    if candidates[:2] == ["progress", "bar"]:
        return "progress_bar", 2
    if len(candidates) >= 2 and candidates[0] == "side" and candidates[1] == "bar":
        return "sidebar", 2
    return "_".join(candidates[:2]), 1


def build_codespeak(request: str, root: Path | None = None) -> CodeSpeakResult:
    tokens = tokenize_request(request)
    action, action_score = _infer_action(tokens)
    layer, layer_score = _infer_layer(tokens)
    target = _infer_target(tokens, layer)
    subject, subject_score = _infer_subject(tokens, layer, action)
    patch_points, points_score = _extract_patch_points(request, action)
    if patch_points.get("operation") == "move" and action != "move":
        action = "move"
        subject, subject_score = _infer_subject(tokens, layer, action)
    total = action_score + layer_score + subject_score
    total += points_score
    confidence = "high" if total >= 5 else "medium" if total >= 3 else "low"
    clarifying_questions = []
    if confidence == "low":
        clarifying_questions = [
            "어느 화면이나 파일을 바꾸고 싶은지 더 구체적으로 말해줄 수 있나요?",
            "추가인지 수정인지, 또는 버그 수정인지 알려줄 수 있나요?",
        ]
    interpretation = (
        f"'{request}' 요청을 {layer} 영역의 {subject} {action} 작업으로 해석했습니다."
    )
    target_file = None
    target_anchor = None
    if root is not None:
        try:
            from vibelign.core.patch_suggester import suggest_patch

            suggestion = suggest_patch(root, request)
            target_file = suggestion.target_file
            target_anchor = suggestion.target_anchor
        except Exception:
            pass

    intent_ir = IntentIR(
        raw_request=request,
        operation=patch_points.get("operation", action),
        source=patch_points.get("source", ""),
        destination=patch_points.get("destination", ""),
        behavior_constraint=patch_points.get("behavior_constraint", ""),
        layer=layer,
        target=target,
        subject=subject,
        action=action,
        confidence=confidence,
        clarifying_questions=clarifying_questions,
    )

    return CodeSpeakResult(
        codespeak=f"{layer}.{target}.{subject}.{action}",
        layer=layer,
        target=target,
        subject=subject,
        action=action,
        confidence=confidence,
        interpretation=interpretation,
        clarifying_questions=clarifying_questions,
        patch_points=patch_points,
        intent_ir=intent_ir,
        target_file=target_file,
        target_anchor=target_anchor,
    )


# === ANCHOR: CODESPEAK_END ===
