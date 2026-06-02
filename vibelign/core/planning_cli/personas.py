from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanningPersona:
    id: str
    name: str
    adapter: str


GIO_PERSONA = PlanningPersona(id="gio", name="지오", adapter="codex")


def persona_for_adapter(adapter: str) -> PlanningPersona:
    if adapter == "codex":
        return GIO_PERSONA
    raise ValueError(f"unsupported planning adapter: {adapter}")
