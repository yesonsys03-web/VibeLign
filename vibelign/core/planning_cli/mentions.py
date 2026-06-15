# === ANCHOR: MENTIONS_START ===
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from vibelign.core.planning_cli.personas import ORDERED_PERSONAS

PersonaAliasGroup = tuple[str, tuple[str, ...]]

# 자동 실행 기본 세트에서 클로이(claude)는 제외한다 — claude -p 가 구독 크레딧/API 로
# 과금될 수 있어, @모두/멘션 없음 같은 암묵 실행에는 넣지 않는다. 클로이는 사용자가
# `@클로이`로 명시할 때만 실행된다(opt-in). GUI 측 클로이 기본 OFF 와 같은 취지.
DEFAULT_PERSONA_IDS: Final[tuple[str, ...]] = tuple(
    persona.id for persona in ORDERED_PERSONAS if persona.id != "chloe"
)
MENTION_ALIASES: Final[tuple[PersonaAliasGroup, ...]] = tuple(
    (persona.id, (persona.id, persona.name)) for persona in ORDERED_PERSONAS
)
ALL_ALIASES: Final[tuple[str, ...]] = ("all", "모두")


@dataclass(frozen=True, slots=True)
# === ANCHOR: MENTIONS_PERSONAMENTIONRESULT_START ===
class PersonaMentionResult:
    persona_ids: tuple[str, ...]
    used_default: bool
    clean_text: str
# === ANCHOR: MENTIONS_PERSONAMENTIONRESULT_END ===


# === ANCHOR: MENTIONS_RESOLVE_PERSONA_MENTIONS_START ===
def resolve_persona_mentions(text: str) -> PersonaMentionResult:
    normalized = text.lower()
    clean_text = _clean_mentions(text)
    if _has_any_alias(normalized, ALL_ALIASES):
        return PersonaMentionResult(
            persona_ids=DEFAULT_PERSONA_IDS,
            used_default=False,
            clean_text=clean_text,
        )

    matched = tuple(
        persona_id
        for persona_id, aliases in MENTION_ALIASES
        if _has_any_alias(normalized, aliases)
    )
    if matched:
        return PersonaMentionResult(
            persona_ids=matched,
            used_default=False,
            clean_text=clean_text,
        )
    return PersonaMentionResult(
        persona_ids=DEFAULT_PERSONA_IDS,
        used_default=True,
        clean_text=text.strip(),
    )
# === ANCHOR: MENTIONS_RESOLVE_PERSONA_MENTIONS_END ===


# === ANCHOR: MENTIONS__HAS_ANY_ALIAS_START ===
def _has_any_alias(text: str, aliases: tuple[str, ...]) -> bool:
    return any(f"@{alias}" in text for alias in aliases)
# === ANCHOR: MENTIONS__HAS_ANY_ALIAS_END ===


# === ANCHOR: MENTIONS__CLEAN_MENTIONS_START ===
def _clean_mentions(text: str) -> str:
    aliases = [*ALL_ALIASES]
    for _, alias_group in MENTION_ALIASES:
        aliases.extend(alias_group)
    escaped = "|".join(re.escape(alias) for alias in aliases)
    pattern = rf"@(?:{escaped})[가-힣a-zA-Z0-9_-]*"
    return re.sub(r"\s+", " ", re.sub(pattern, "", text, flags=re.IGNORECASE)).strip()
# === ANCHOR: MENTIONS__CLEAN_MENTIONS_END ===
# === ANCHOR: MENTIONS_END ===
