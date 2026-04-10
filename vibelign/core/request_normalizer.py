# === ANCHOR: REQUEST_NORMALIZER_START ===
"""사용자 요청 전처리·다중 의도 분리 (patch_upgrade §6.3 순번 5).

codespeak 파서에 넘기기 전에 공백·반복 추임새를 정리하고,
접속사·구분자 기준으로 sub_intent 후보를 나눈다.
쉼표 단독 분할은 동작이 둘 다 잡힐 때만 허용해 오분할을 줄인다.
"""

from __future__ import annotations

import re


_ACTION_HINT_WORDS = {
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
    "move",
    "move to",
    "relocate",
    "transfer",
    "reposition",
    "이동",
    "옮겨",
    "옮기",
    "배치",
    "붙여",
    "배치해",
    "이관",
    "이동해",
    "옮겨줘",
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
    "변경해",
    "업데이트",
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
    "apply",
    "set",
    "enable",
    "activate",
    "적용",
    "설정",
    "활성화",
    "켜줘",
    "적용해",
}


# === ANCHOR: REQUEST_NORMALIZER__NORMALIZE_WHITESPACE_START ===
def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


# === ANCHOR: REQUEST_NORMALIZER__NORMALIZE_WHITESPACE_END ===


# === ANCHOR: REQUEST_NORMALIZER__COLLAPSE_REDUNDANT_FILLERS_START ===
def _collapse_redundant_fillers(text: str) -> str:
    t = text
    t = re.sub(r"(해줘\s*){2,}", "해줘 ", t)
    t = re.sub(r"(해주세요\s*){2,}", "해주세요 ", t)
    t = re.sub(r"(해줄래\s*){2,}", "해줄래 ", t)
    t = re.sub(r"(please\s*){2,}", "please ", t, flags=re.IGNORECASE)
    t = re.sub(r"(pls\s*){2,}", "pls ", t, flags=re.IGNORECASE)
    t = re.sub(r"(감사합니다\s*){2,}", "감사합니다 ", t)
    t = re.sub(r"(ㅋ\s*){3,}", "", t)
    t = re.sub(r"[!?]{3,}", "!", t)
    return t.strip()


# === ANCHOR: REQUEST_NORMALIZER__COLLAPSE_REDUNDANT_FILLERS_END ===


# === ANCHOR: REQUEST_NORMALIZER__COLLAPSE_REPEATED_CONJUNCTIONS_START ===
def _collapse_repeated_conjunctions(text: str) -> str:
    t = re.sub(r"(?:\b(and|then)\b\s+){2,}", r"\1 ", text, flags=re.IGNORECASE)
    t = re.sub(r"(?:그리고\s+){2,}", "그리고 ", t)
    return t.strip()


# === ANCHOR: REQUEST_NORMALIZER__COLLAPSE_REPEATED_CONJUNCTIONS_END ===


# === ANCHOR: REQUEST_NORMALIZER__SPLIT_NUMBERED_SEGMENTS_START ===
def _split_numbered_segments(text: str) -> list[str] | None:
    if "\n" not in text.strip():
        return None
    raw_lines = text.split("\n")
    hits = sum(1 for ln in raw_lines if re.match(r"^\s*\d+[\.\)]\s+\S", ln.strip()))
    if hits < 2:
        return None
    chunks = re.split(r"\n\s*(?=\d+[\.\)]\s+\S)", text)
    out: list[str] = []
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        if not re.match(r"^\d+[\.\)]\s+\S", c):
            continue
        c = re.sub(r"^\d+[\.\)]\s+", "", c).strip()
        if c:
            out.append(c)
    return out if len(out) >= 2 else None


# 강한 구분자만 (쉼표 제외) — §6.3 오분할 방지
# === ANCHOR: REQUEST_NORMALIZER__SPLIT_NUMBERED_SEGMENTS_END ===
_STRONG_SPLIT_RE = re.compile(
    r"(?:;|；|\s+그리고\s+|\s+또한\s+|\s+및\s+|\s+이랑\s+"
    r"|\s+\band\b\s+|\s+\bthen\b\s+|\s+\balso\b\s+|\s+\bplus\b\s+)",
    re.IGNORECASE,
)


def _tokenize_request(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_가-힣]+", text.lower())


def _looks_like_behavior_clause(text: str) -> bool:
    normalized = text.strip().lower()
    return any(
        marker in normalized
        for marker in (
            "클릭하면",
            "유지",
            "보존",
            "해야 돼",
            "해야해",
            "해야 해",
            "해야 합니다",
            "해야합니다",
            "동작해야",
            "동작해",
        )
    )


def _has_explicit_action(text: str) -> bool:
    for token in _tokenize_request(text):
        if token in _ACTION_HINT_WORDS:
            return True
        if any(len(word) >= 2 and word in token for word in _ACTION_HINT_WORDS):
            return True
    return False


# === ANCHOR: REQUEST_NORMALIZER__SPLIT_SUB_INTENTS_IMPL_START ===
def _split_sub_intents_impl(normalized: str) -> list[str]:
    if not normalized:
        return []
    numbered = _split_numbered_segments(normalized)
    if numbered:
        return numbered

    parts = [p.strip() for p in _STRONG_SPLIT_RE.split(normalized) if p.strip()]
    if len(parts) > 1:
        if any(_looks_like_behavior_clause(p) for p in parts[1:]):
            return [normalized]
        explicit = sum(1 for p in parts if _has_explicit_action(p))
        if explicit >= 2:
            return parts
        return [normalized]

    # 단일 덩어리: 쉼표는 두 조각 모두에 동작 힌트가 있을 때만 분리
    if "," in normalized or "，" in normalized:
        comma_parts = [
            p.strip() for p in re.split(r"[,，]\s*", normalized) if p.strip()
        ]
        if len(comma_parts) <= 1:
            return [normalized]
        if any(_looks_like_behavior_clause(p) for p in comma_parts[1:]):
            return [normalized]
        explicit = sum(1 for p in comma_parts if _has_explicit_action(p))
        if explicit >= 2:
            return comma_parts
    return [normalized]


# === ANCHOR: REQUEST_NORMALIZER__SPLIT_SUB_INTENTS_IMPL_END ===


# === ANCHOR: REQUEST_NORMALIZER_NORMALIZE_USER_REQUEST_START ===
def normalize_user_request(raw: str) -> tuple[str, list[str]]:
    """정제 문자열과 sub_intent 목록(길이 1이면 단일 의도)."""
    stripped = raw.strip()
    if not stripped:
        return "", []
    numbered = _split_numbered_segments(stripped)
    if numbered:
        cleaned_segments: list[str] = []
        for seg in numbered:
            x = _normalize_whitespace(seg)
            x = _collapse_redundant_fillers(x)
            x = _collapse_repeated_conjunctions(x)
            cleaned_segments.append(x)
        t = _normalize_whitespace(stripped)
        t = _collapse_redundant_fillers(t)
        t = _collapse_repeated_conjunctions(t)
        return t, cleaned_segments
    t = _normalize_whitespace(stripped)
    t = _collapse_redundant_fillers(t)
    t = _collapse_repeated_conjunctions(t)
    parts = _split_sub_intents_impl(t)
    if not parts:
        return t, [t]
    return t, parts


# === ANCHOR: REQUEST_NORMALIZER_NORMALIZE_USER_REQUEST_END ===


# === ANCHOR: REQUEST_NORMALIZER_CLEANED_STRING_ONLY_START ===
def cleaned_string_only(raw: str) -> str:
    """토큰화 직전 정제 문자열만 필요할 때."""
    s, _ = normalize_user_request(raw)
    return s


# === ANCHOR: REQUEST_NORMALIZER_CLEANED_STRING_ONLY_END ===
# === ANCHOR: REQUEST_NORMALIZER_END ===
