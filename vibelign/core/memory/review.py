# === ANCHOR: MEMORY_REVIEW_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast

from vibelign.core.memory.models import MemoryState
from vibelign.core.memory.store import load_memory_state


class _RedactedMemorySummaryLike(Protocol):
    active_intent: str
    next_action: str
    decisions: list[str]
    relevant_files: list[str]
    observed_context: list[str]
    verification: list[str]
    warnings: list[str]
    redaction: object


class _MemoryFreshnessLike(Protocol):
    verification_freshness: str
    stale_verification_commands: list[str]
    stale_intent: bool
    stale_relevant_files: list[str]


_BuildRedactedSummary = Callable[[MemoryState], _RedactedMemorySummaryLike]
_AssessMemoryFreshness = Callable[[MemoryState], _MemoryFreshnessLike]


@dataclass(frozen=True)
class _ZeroRedaction:
    secret_hits: int = 0
    privacy_hits: int = 0
    summarized_fields: int = 0


def _zero_redaction() -> object:
    return _ZeroRedaction()


@dataclass(frozen=True)
class MemoryReview:
    has_memory: bool
    active_intent: str = ""
    next_action: str = ""
    decisions: list[str] = field(default_factory=list)
    relevant_files: list[str] = field(default_factory=list)
    observed_context: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    downgrade_warning: str = ""
    redaction: object = field(default_factory=_zero_redaction)
    suggestions: list[str] = field(default_factory=list)


def review_memory(path: Path) -> MemoryReview:
    state = load_memory_state(path)
    if not _has_memory(state):
        return MemoryReview(
            has_memory=False,
            suggestions=['Add a decision with: vib memory decide "..."'],
        )

    suggestions: list[str] = []
    redacted = _build_redacted_memory_summary()(state)
    freshness = _assess_memory_freshness()(state)
    active_intent = redacted.active_intent
    next_action = redacted.next_action
    warnings = list(redacted.warnings)
    if state.downgrade_warning:
        warnings.append(state.downgrade_warning)

    if not active_intent:
        suggestions.append('Confirm the current goal with: vib memory decide "..."')
    if not next_action:
        suggestions.append("Capture the next handoff action with --first-next-action.")
    if freshness.stale_verification_commands:
        last_cmd = redacted.verification[-1].partition(" -> ")[0].strip() if redacted.verification else ""
        last_cmd = last_cmd.partition(" (stale")[0].strip()
        if last_cmd:
            suggestions.append(f"Rerun stale verification: {last_cmd}")
    if freshness.stale_intent:
        suggestions.append("Review stale intent or next action before handoff.")
    if freshness.stale_relevant_files:
        suggestions.append("Review stale relevant files before handoff.")
    if warnings:
        suggestions.append("Review warnings before using this memory as handoff truth.")

    return MemoryReview(
        has_memory=True,
        active_intent=active_intent,
        next_action=next_action,
        decisions=redacted.decisions,
        relevant_files=redacted.relevant_files,
        observed_context=redacted.observed_context,
        verification=redacted.verification,
        warnings=warnings,
        downgrade_warning=state.downgrade_warning,
        redaction=redacted.redaction,
        suggestions=suggestions,
    )


def _has_memory(state: MemoryState) -> bool:
    return bool(
        state.active_intent
        or state.decisions
        or state.relevant_files
        or state.verification
        or state.risks
        or state.next_action
        or state.observed_context
        or state.downgrade_warning
    )


def _build_redacted_memory_summary() -> _BuildRedactedSummary:
    module = import_module("vibelign.core.memory.redaction")
    return cast(_BuildRedactedSummary, getattr(module, "build_redacted_memory_summary"))


def _assess_memory_freshness() -> _AssessMemoryFreshness:
    module = import_module("vibelign.core.memory.freshness")
    return cast(_AssessMemoryFreshness, getattr(module, "assess_memory_freshness"))
# === ANCHOR: MEMORY_REVIEW_END ===
