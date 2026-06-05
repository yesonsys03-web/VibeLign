# === ANCHOR: TOKEN_ALIASES_START ===
from __future__ import annotations

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


# === ANCHOR: TOKEN_ALIASES_REVERSE_TOKEN_ALIASES_START ===
def reverse_token_aliases() -> dict[str, list[str]]:
    reverse: dict[str, list[str]] = {}
    for korean, english_list in TOKEN_ALIASES.items():
        for english in english_list:
            bucket = reverse.setdefault(english, [])
            if korean not in bucket:
                bucket.append(korean)
    return reverse
# === ANCHOR: TOKEN_ALIASES_REVERSE_TOKEN_ALIASES_END ===
# === ANCHOR: TOKEN_ALIASES_END ===
