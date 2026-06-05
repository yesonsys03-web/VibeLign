# === ANCHOR: RESPONSE_POLICY_START ===
from __future__ import annotations

from typing import Final

from vibelign.core.planning_cli.cli_adapters import PlanningCliStatus

FORBIDDEN_LLM_TERMS: Final = ("codespeak", "target_anchor", "patch")


# === ANCHOR: RESPONSE_POLICY_SAFE_PLANNING_STATUS_START ===
def safe_planning_status(status: PlanningCliStatus, stdout: str) -> str:
    if status == "ok" and _contains_forbidden_terms(stdout):
        return "bad_output"
    return status
# === ANCHOR: RESPONSE_POLICY_SAFE_PLANNING_STATUS_END ===


# === ANCHOR: RESPONSE_POLICY__CONTAINS_FORBIDDEN_TERMS_START ===
def _contains_forbidden_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_LLM_TERMS)
# === ANCHOR: RESPONSE_POLICY__CONTAINS_FORBIDDEN_TERMS_END ===
# === ANCHOR: RESPONSE_POLICY_END ===
