# === ANCHOR: RECOVERY_PACKAGE_START ===
"""Read-only recovery planning primitives."""

from .models import (
    DriftCandidate,
    IntentZoneEntry,
    NormalizedPath,
    RecoveryOption,
    RecoveryPlan,
    RecoverySignalSet,
    SafeCheckpointCandidate,
)
from .apply import (
    RecoveryApplyFeatureGate,
    RecoveryApplyRequest,
    RecoveryApplyReadiness,
    RecoveryApplySummary,
    RecoveryApplyValidation,
    RecoveryCheckpointSandwichPrecondition,
    RecoveryExplicitConfirmationPrecondition,
    RecoveryPathMatchPrecondition,
    RecoveryProjectLockPrecondition,
    check_recovery_apply_readiness,
    validate_recovery_apply_request,
)
from .locks import (
    acquire_recovery_lock,
    read_recovery_lock,
    recovery_lock_path,
    release_recovery_lock,
    RecoveryLockAcquireResult,
    RecoveryLockState,
    RecoveryLockStatus,
)
from .path import PathSafetyError, normalize_recovery_path
from .planner import build_recovery_plan

__all__ = [
    "DriftCandidate",
    "IntentZoneEntry",
    "NormalizedPath",
    "PathSafetyError",
    "RecoveryApplyFeatureGate",
    "RecoveryApplyRequest",
    "RecoveryApplyReadiness",
    "RecoveryApplySummary",
    "RecoveryApplyValidation",
    "RecoveryCheckpointSandwichPrecondition",
    "RecoveryExplicitConfirmationPrecondition",
    "RecoveryPathMatchPrecondition",
    "RecoveryProjectLockPrecondition",
    "RecoveryOption",
    "RecoveryPlan",
    "RecoverySignalSet",
    "RecoveryLockState",
    "RecoveryLockAcquireResult",
    "RecoveryLockStatus",
    "SafeCheckpointCandidate",
    "acquire_recovery_lock",
    "build_recovery_plan",
    "check_recovery_apply_readiness",
    "normalize_recovery_path",
    "read_recovery_lock",
    "recovery_lock_path",
    "release_recovery_lock",
    "validate_recovery_apply_request",
]
# === ANCHOR: RECOVERY_PACKAGE_END ===
