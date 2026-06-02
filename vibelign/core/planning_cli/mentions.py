from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from vibelign.core.planning_cli.personas import ORDERED_PERSONAS

DEFAULT_PERSONA_IDS: Final = tuple(persona.id for persona in ORDERED_PERSONAS)
MENTION_ALIASES: Final = {
    "chloe": ("chloe", "클로이"),
    "gio": ("gio", "지오"),
    "mina": ("mina", "미나"),
}
ALL_ALIASES: Final = ("all", "모두")


@dataclass(frozen=True, slots=True)
class PersonaMentionResult:
    persona_ids: tuple[str, ...]
    used_default: bool
    clean_text: str


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
        for persona_id in DEFAULT_PERSONA_IDS
        if _has_any_alias(normalized, MENTION_ALIASES[persona_id])
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


def _has_any_alias(text: str, aliases: tuple[str, ...]) -> bool:
    return any(f"@{alias}" in text for alias in aliases)


def _clean_mentions(text: str) -> str:
    aliases = [*ALL_ALIASES]
    for alias_group in MENTION_ALIASES.values():
        aliases.extend(alias_group)
    escaped = "|".join(re.escape(alias) for alias in aliases)
    pattern = rf"@(?:{escaped})[가-힣a-zA-Z0-9_-]*"
    return re.sub(r"\s+", " ", re.sub(pattern, "", text, flags=re.IGNORECASE)).strip()
