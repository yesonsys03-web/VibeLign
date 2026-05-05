# === ANCHOR: RECOVERY_MODELS_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


RecoveryMode = Literal["read_only", "apply_preview", "apply"]
DriftCircuitBreakerState = Literal["active", "degraded"]
RecoveryCandidateSource = Literal[
    "manual_checkpoint",
    "post_commit_checkpoint",
    "git_commit",
    "git_tag",
    "external_backup",
    "verification_snapshot",
    "recovery_sandwich",
]
RestoreCapability = Literal["file_restore", "preview_only", "metadata_only"]
RecommendationProvider = Literal["deterministic", "llm", "invalid", "cache"]
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
    action_type: str = "explain"
    candidate_id: str | None = None
    recommended: bool = False
    risk_level: Literal["low", "medium", "high"] = "low"
    expected_loss: tuple[str, ...] = ()
    next_call: str = "vib recover --preview"


@dataclass(frozen=True)
class SafeCheckpointCandidate:
    checkpoint_id: str
    created_at: str
    message: str
    metadata_complete: bool
    preview_available: bool
    predates_change: bool


@dataclass(frozen=True)
class EvidenceScore:
    commit_boundary: bool = False
    verification_fresh: bool = False
    diff_small: bool = False
    protected_paths_clean: bool = False
    time_match_user_request: bool = False
    formula_version: str = "v1"

    def score(self) -> float:
        if self.formula_version != "v1":
            raise ValueError(f"unsupported evidence formula: {self.formula_version}")
        flags = (
            self.commit_boundary,
            self.verification_fresh,
            self.diff_small,
            self.protected_paths_clean,
            self.time_match_user_request,
        )
        return sum(1 for flag in flags if flag) / len(flags)


@dataclass(frozen=True)
class LLMConfidence:
    level: Literal["high", "medium", "low"]
    reason: str


@dataclass(frozen=True)
class RecoveryCandidate:
    candidate_id: str
    source: RecoveryCandidateSource
    created_at: str
    label: str
    commit_hash: str | None = None
    commit_message: str | None = None
    restore_capability: RestoreCapability = "preview_only"
    preview_available: bool = False
    changed_files_since_previous: tuple[str, ...] = ()
    verification_nearby: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMRankingItem:
    candidate_id: str
    rank: int
    llm_confidence: LLMConfidence
    reason: str
    expected_loss: tuple[str, ...] = ()
    recommended_action_type: str = "preview_file_restore"
    requires_user_confirmation: bool = True


@dataclass(frozen=True)
class LLMRankingResponse:
    interpreted_goal: str
    ranked: tuple[LLMRankingItem, ...]
    uncertainties: tuple[str, ...] = ()
    should_apply: bool = False
    should_write_memory: bool = False


@dataclass(frozen=True)
class RecoveryRecommendation:
    candidate: RecoveryCandidate
    rank: int
    evidence_score: EvidenceScore
    llm_confidence: LLMConfidence | None = None
    reason: str = ""
    expected_loss: tuple[str, ...] = ()
    provider: RecommendationProvider = "deterministic"


@dataclass(frozen=True)
class RankedCandidatePayload:
    candidate_id: str
    rank: int
    evidence_score: dict[str, object]
    llm_confidence: dict[str, str] | None = None
    reason: str = ""
    expected_loss: tuple[str, ...] = ()


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
    ranked_candidates: list[RankedCandidatePayload] = field(default_factory=list)
    recommendation_provider: str | None = None

# === ANCHOR: RECOVERY_MODELS_END ===
