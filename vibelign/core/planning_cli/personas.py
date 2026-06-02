from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class PlanningPersona:
    id: str
    name: str
    adapter: str
    section_title: str
    prompt_role: str


CHLOE_PERSONA: Final = PlanningPersona(
    id="chloe",
    name="클로이",
    adapter="claude",
    section_title="클로이의 설계",
    prompt_role="설계자 클로이",
)
GIO_PERSONA: Final = PlanningPersona(
    id="gio",
    name="지오",
    adapter="codex",
    section_title="지오의 검토",
    prompt_role="검토자 지오",
)
MINA_PERSONA: Final = PlanningPersona(
    id="mina",
    name="미나",
    adapter="agy",
    section_title="미나의 탐색",
    prompt_role="탐색자 미나",
)
ORDERED_PERSONAS: Final = (CHLOE_PERSONA, GIO_PERSONA, MINA_PERSONA)
PERSONAS_BY_ID: Final = {persona.id: persona for persona in ORDERED_PERSONAS}


def persona_for_adapter(adapter: str) -> PlanningPersona:
    for persona in ORDERED_PERSONAS:
        if persona.adapter == adapter:
            return persona
    raise ValueError(f"unsupported planning adapter: {adapter}")


def persona_for_id(persona_id: str) -> PlanningPersona:
    persona = PERSONAS_BY_ID.get(persona_id)
    if persona is None:
        raise ValueError(f"unsupported planning persona: {persona_id}")
    return persona


def ordered_personas_for_ids(persona_ids: tuple[str, ...]) -> tuple[PlanningPersona, ...]:
    requested = set(persona_ids)
    return tuple(persona for persona in ORDERED_PERSONAS if persona.id in requested)
