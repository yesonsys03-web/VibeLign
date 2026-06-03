from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from vibelign.core.planning_cli.personas import ORDERED_PERSONAS

PersonaAliasGroup = tuple[str, tuple[str, ...]]

DEFAULT_PERSONA_IDS: Final[tuple[str, ...]] = tuple(persona.id for persona in ORDERED_PERSONAS)
MENTION_ALIASES: Final[tuple[PersonaAliasGroup, ...]] = tuple(
    (persona.id, (persona.id, persona.name)) for persona in ORDERED_PERSONAS
)
ALL_ALIASES: Final[tuple[str, ...]] = ("all", "모두")


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


def _has_any_alias(text: str, aliases: tuple[str, ...]) -> bool:
    return any(f"@{alias}" in text for alias in aliases)


def _clean_mentions(text: str) -> str:
    aliases = [*ALL_ALIASES]
    for _, alias_group in MENTION_ALIASES:
        aliases.extend(alias_group)
    escaped = "|".join(re.escape(alias) for alias in aliases)
    pattern = rf"@(?:{escaped})[가-힣a-zA-Z0-9_-]*"
    return re.sub(r"\s+", " ", re.sub(pattern, "", text, flags=re.IGNORECASE)).strip()
