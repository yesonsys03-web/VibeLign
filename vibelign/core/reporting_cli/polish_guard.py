# === ANCHOR: POLISH_GUARD_START ===
from __future__ import annotations

import re
from collections import Counter

# 천단위 콤마를 포함한 숫자 런. 단위(%, 만, 원 등)는 무시하고 숫자 자체만 본다.
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm(token: str) -> str:
    """천단위 콤마 제거 + 정수 토큰의 선행 0 제거('06'→'6')."""
    t = token.replace(",", "")
    return str(int(t)) if t.isdigit() else t


def extract_numbers(text: str) -> set[str]:
    """문자열의 숫자 토큰을 정규화한 집합으로 반환한다."""
    return {_norm(m) for m in _NUM.findall(text)}


def _counts(text: str) -> Counter[str]:
    return Counter(_norm(m) for m in _NUM.findall(text))


# 보고 한 문장 다듬기에는 안 나오는 강한 비-응답 신호들. 보수적으로(강신호만) 판정한다.
_NONANSWER_MARKERS = (
    "다듬어 드릴까요", "어떤 문장", "문장을 알려", "원문을 알려",
    "please provide", "i don't see", "clarification",
)


def looks_like_non_answer(original: str, polished: str) -> bool:
    """provider 가 다듬은 문장 대신 거부·되묻기·메타응답을 돌려줬는지 보수적으로 판정한다.
    True 면 호출자가 원문을 유지해야 한다(좋은 다듬기를 되돌리지 않도록 강신호만 본다)."""
    p = polished.strip()
    # 1) 마크다운 구조: 보고 한 문장엔 ** 나 머리글(#) 이 안 나온다.
    if "**" in p or p.startswith("#") or "\n#" in p:
        return True
    # 2) 멀티라인 + 원문보다 크게 길어짐(한 문장 다듬기가 문단으로 부풀음).
    if "\n" in p and len(p) > len(original) + 40:
        return True
    # 3) 길이 폭증(군더더기만 덜어내라 했으므로 4배+ 는 비정상).
    if len(p) > len(original) * 4 + 40:
        return True
    # 4) 되묻기/거부 키워드 + 물음표(사용자에게 질문을 되던짐).
    low = p.lower()
    if "?" in p and any(m.lower() in low for m in _NONANSWER_MARKERS):
        return True
    return False


def guard_polished(original: str, polished: str) -> tuple[bool, str, list[str]]:
    """다듬은 문장이 원문의 숫자를 그대로 보존하고 새 숫자를 안 만들었는지 검증한다.
    반환: (ok, reason, missing). ok=False 면 호출자가 원문을 유지해야 한다.
    reason: '' | 'number_dropped' | 'number_added' | 'number_changed'."""
    orig = _counts(original)
    pol = _counts(polished)
    missing = sorted((orig - pol).keys())
    added = sorted((pol - orig).keys())
    if not missing and not added:
        return True, "", []
    if missing and added:
        return False, "number_changed", missing
    if missing:
        return False, "number_dropped", missing
    return False, "number_added", missing
# === ANCHOR: POLISH_GUARD_END ===
