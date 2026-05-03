# === ANCHOR: MEMORY_HANDOFF_REVIEW_START ===
from __future__ import annotations

from pathlib import Path

from vibelign.core.memory.redaction import MemoryRedaction, build_redacted_memory_summary
from vibelign.core.memory.store import load_memory_state


def build_handoff_review(path: Path) -> dict[str, object]:
    state = load_memory_state(path)
    summary = build_redacted_memory_summary(state)
    return {
        "read_only": state.read_only,
        "downgrade_warning": state.downgrade_warning,
        "active_intent": summary.active_intent,
        "next_action": summary.next_action,
        "decisions": summary.decisions,
        "relevant_files": summary.relevant_files,
        "observed_context": summary.observed_context,
        "verification": summary.verification,
        "warnings": summary.warnings,
        "redaction": _redaction_payload(summary.redaction),
    }


def _redaction_payload(redaction: MemoryRedaction) -> dict[str, int]:
    return {
        "secret_hits": redaction.secret_hits,
        "privacy_hits": redaction.privacy_hits,
        "summarized_fields": redaction.summarized_fields,
    }
# === ANCHOR: MEMORY_HANDOFF_REVIEW_END ===
