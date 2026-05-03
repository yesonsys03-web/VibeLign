# === ANCHOR: RECOVERY_RENDER_START ===
from __future__ import annotations

from .models import RecoveryPlan


# === ANCHOR: RECOVERY_RENDER__RENDER_TEXT_PLAN_START ===
def render_text_plan(plan: RecoveryPlan) -> str:
    lines = [
        "VibeLign Recovery Advisor (read-only)",
        "No files were modified.",
        f"Summary: {plan.summary}",
        "",
        "Recommended options:",
    ]
    for index, option in enumerate(plan.options, start=1):
        suffix = f" (blocked: {option.blocked_reason})" if option.blocked_reason else ""
        lines.append(f"{index}. Level {option.level}: {option.label}{suffix}")
    if plan.drift_candidates:
        lines.extend(["", "Drift candidates (review before any restore):"])
        for candidate in plan.drift_candidates:
            lines.append(f"- {candidate.path}: {candidate.why_outside_zone}")
    if plan.safe_checkpoint_candidate is not None:
        lines.extend(
            [
                "",
                "Safe checkpoint candidate:",
                f"- {plan.safe_checkpoint_candidate.checkpoint_id}: {plan.safe_checkpoint_candidate.message or '(no message)'}",
                f"  metadata complete: {plan.safe_checkpoint_candidate.metadata_complete}; preview available: {plan.safe_checkpoint_candidate.preview_available}; predates change: {plan.safe_checkpoint_candidate.predates_change}",
            ]
        )
    return "\n".join(lines)
# === ANCHOR: RECOVERY_RENDER__RENDER_TEXT_PLAN_END ===

# === ANCHOR: RECOVERY_RENDER_END ===
