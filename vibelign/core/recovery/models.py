# === ANCHOR: RECOVERY_MODELS_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


RecoveryMode = Literal["read_only", "apply_preview", "apply"]
DriftCircuitBreakerState = Literal["active", "degraded"]
IntentZoneSource = Literal[
    "explicit",
    "recent_patch_target",
    "project_map_category",
    "anchor_co_occurrence",
    "diff_fallback",
]


@dataclass(frozen=True)
class NormalizedPath:
    absolute_path: Path
    relative_path: str
    display_path: str
    was_absolute_input: bool = False


@dataclass(frozen=True)
class IntentZoneEntry:
    path: str
    source: IntentZoneSource
    reason: str


@dataclass(frozen=True)
class DriftCandidate:
    path: str
    why_outside_zone: str
    suggested_action: str = "review_and_revert_if_unintentional"
    requires_user_review: bool = True


@dataclass(frozen=True)
class RecoveryOption:
    option_id: str
    level: int
    label: str
    affected_paths: list[str] = field(default_factory=list)
    estimated_impact: str = "no file changes; informational"
    requires_sandwich: bool = False
    requires_lock: bool = False
    blocked_reason: str | None = None


@dataclass(frozen=True)
class SafeCheckpointCandidate:
    checkpoint_id: str
    created_at: str
    message: str
    metadata_complete: bool
    preview_available: bool
    predates_change: bool


@dataclass(frozen=True)
class RecoverySignalSet:
    changed_paths: list[str] = field(default_factory=list)
    untracked_paths: list[str] = field(default_factory=list)
    explicit_relevant_paths: list[str] = field(default_factory=list)
    recent_patch_paths: list[str] = field(default_factory=list)
    project_map_categories: dict[str, str] = field(default_factory=dict)
    anchor_intents_by_path: dict[str, list[str]] = field(default_factory=dict)
    safe_checkpoint_candidate: SafeCheckpointCandidate | None = None
    guard_has_failures: bool = False
    guard_summary: str = ""
    explain_summary: str = ""
    drift_accuracy_window_size: int = 0
    drift_accuracy_confirmed_correct: int = 0
    drift_accuracy_confirmed_incorrect: int = 0


@dataclass(frozen=True)
class RecoveryPlan:
    plan_id: str
    mode: RecoveryMode
    level: int
    summary: str
    intent_zone: list[IntentZoneEntry] = field(default_factory=list)
    drift_candidates: list[DriftCandidate] = field(default_factory=list)
    options: list[RecoveryOption] = field(default_factory=list)
    safe_checkpoint_candidate: SafeCheckpointCandidate | None = None
    no_files_modified: bool = True
    circuit_breaker_state: DriftCircuitBreakerState = "active"

# === ANCHOR: RECOVERY_MODELS_END ===
