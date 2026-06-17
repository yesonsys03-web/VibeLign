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
