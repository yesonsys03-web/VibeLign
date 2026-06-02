from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanningInput:
    idea: str
    language: str = "auto"
    output: str | None = None
    force: bool = False


@dataclass(frozen=True)
class PlanningResult:
    output_path: str
    absolute_output_path: str
    markdown: str
    fallback_reason: str
    session_id: str
