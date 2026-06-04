from __future__ import annotations

import re
from pathlib import Path

KOREAN_PARTICLE_SUFFIXES: tuple[str, ...] = (
    "입니다",
    "에서",
    "으로",
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
KOREAN_PARTICLE_SUFFIXES_SORTED = tuple(
    sorted(KOREAN_PARTICLE_SUFFIXES, key=len, reverse=True)
)

TOKEN_ALIASES: dict[str, list[str]] = {
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
    "토큰": ["token", "auth"],
    "발급": ["generate", "issue", "token"],
    "저장": ["save", "store", "update"],
    "평문": ["hash", "encrypt", "plaintext"],
    "해시": ["hash", "encrypt"],
    "중복": ["duplicate", "create", "unique"],
    "캐시": ["cache", "database"],
    "느려": ["performance", "optimize"],
}
KOREAN_ALIAS_KEYS = tuple(
    sorted(
        (key for key in TOKEN_ALIASES if re.fullmatch(r"[가-힣]+", key)),
        key=len,
        reverse=True,
    )
)

PASCAL_SPLIT_RE1 = re.compile(r"([A-Z]+)([A-Z][a-z])")
PASCAL_SPLIT_RE2 = re.compile(r"([a-z0-9])([A-Z])")


def decompose_korean_compound(token: str) -> list[str]:
    if not re.fullmatch(r"[가-힣]+", token):
        return []
    if token in TOKEN_ALIASES:
        return []
    parts: list[str] = []
    index = 0
    token_length = len(token)
    while index < token_length:
        matched_key = ""
        for key in KOREAN_ALIAS_KEYS:
            if token.startswith(key, index):
                matched_key = key
                break
        if not matched_key:
            return []
        parts.append(matched_key)
        index += len(matched_key)
    return parts if len(parts) >= 2 else []


def split_identifier_parts(text: str) -> list[str]:
    parts = re.findall(r"[a-z]+|[0-9]+|[가-힣]+", text.lower())
    return [part for part in parts if part]


def normalize_korean_token(token: str) -> list[str]:
    values = [token]
    for suffix in KOREAN_PARTICLE_SUFFIXES_SORTED:
        if len(token) > len(suffix) + 1 and token.endswith(suffix):
            values.append(token[: -len(suffix)])
            break
    return values


def expand_token(token: str) -> list[str]:
    expanded: list[str] = []
    for candidate in normalize_korean_token(token):
        expanded.append(candidate)
        expanded.extend(split_identifier_parts(candidate))
        expanded.extend(TOKEN_ALIASES.get(candidate, []))
        for part in decompose_korean_compound(candidate):
            expanded.append(part)
            expanded.extend(TOKEN_ALIASES.get(part, []))
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
        for token in expand_token(raw):
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return tokens


def snake_ify_path(text: str) -> str:
    return PASCAL_SPLIT_RE2.sub(r"\1_\2", PASCAL_SPLIT_RE1.sub(r"\1_\2", text))


def path_tokens(path: Path | str) -> set[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9]+|[가-힣]+", snake_ify_path(str(path)).lower())
    tokens: set[str] = set()
    for raw in raw_tokens:
        for token in expand_token(raw):
            tokens.add(token)
    return tokens


def intent_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-zA-Z0-9_]+|[가-힣]+", text.lower()):
        for token in expand_token(raw):
            tokens.add(token)
    return tokens


def reverse_token_aliases() -> dict[str, list[str]]:
    reverse: dict[str, list[str]] = {}
    for korean, english_list in TOKEN_ALIASES.items():
        for english in english_list:
            bucket = reverse.setdefault(english, [])
            if korean not in bucket:
                bucket.append(korean)
    return reverse
