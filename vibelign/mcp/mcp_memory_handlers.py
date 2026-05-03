from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from vibelign.core.memory.audit import (
    append_memory_audit_event,
    build_memory_audit_event,
    memory_audit_path,
)
from vibelign.core.memory.redaction import build_redacted_memory_summary
from vibelign.core.memory.store import load_memory_state
from vibelign.core.meta_paths import MetaPaths


class TextContentFactory(Protocol):
    def __call__(self, *, type: str, text: str) -> object: ...


def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]


def handle_memory_summary_read(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    _ = arguments
    state = load_memory_state(MetaPaths(root).work_memory_path)
    summary = build_redacted_memory_summary(state)
    append_memory_audit_event(
        memory_audit_path(root),
        build_memory_audit_event(
            root,
            event="memory_summary_read",
            tool="mcp",
            redaction=summary.redaction,
        ),
    )
    payload: dict[str, object] = {
        "ok": True,
        "source": ".vibelign/work_memory.json",
        "provenance": "redacted_typed_memory_summary",
        "read_only": True,
        "active_intent": summary.active_intent,
        "next_action": summary.next_action,
        "decisions": summary.decisions,
        "relevant_files": summary.relevant_files,
        "observed_context": summary.observed_context,
        "verification": summary.verification,
        "warnings": summary.warnings,
        "redaction": {
            "secret_hits": summary.redaction.secret_hits,
            "privacy_hits": summary.redaction.privacy_hits,
            "summarized_fields": summary.redaction.summarized_fields,
        },
    }
    if state.downgrade_warning:
        payload["warnings"] = summary.warnings + [state.downgrade_warning]
    return _text(text_content, json.dumps(payload, ensure_ascii=False, sort_keys=True))
