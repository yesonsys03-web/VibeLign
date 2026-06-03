from __future__ import annotations

from typing import Final

from vibelign.core.planning_cli.cli_adapters import PlanningCliStatus

FORBIDDEN_LLM_TERMS: Final = ("codespeak", "target_anchor", "patch")


def safe_planning_status(status: PlanningCliStatus, stdout: str) -> str:
    if status == "ok" and _contains_forbidden_terms(stdout):
        return "bad_output"
    return status


def _contains_forbidden_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_LLM_TERMS)
