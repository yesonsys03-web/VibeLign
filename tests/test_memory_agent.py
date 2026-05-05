import argparse
import json
from pathlib import Path
from unittest import mock

from vibelign.commands.vib_transfer_cmd import run_transfer
from vibelign.core.memory.agent import (
    accept_handoff_draft_field,
    build_handoff_summary_draft,
    dismiss_handoff_draft_field,
    handoff_draft_to_payload,
    undo_recent_handoff_acceptance,
)
from vibelign.core.memory.models import MemoryObservedContext, MemoryState, MemoryTextField
from vibelign.core.memory.store import load_memory_state, save_memory_state


def test_handoff_draft_create_is_reviewable_without_writing_memory(tmp_path: Path) -> None:
    memory_path = tmp_path / ".vibelign" / "work_memory.json"

    draft = build_handoff_summary_draft(
        memory_path,
        {
            "session_summary": "Finish recovery audit wiring",
            "first_next_action": "Run recovery tests",
            "verification": ["uv run pytest tests/test_memory_agent.py -> passed"],
        },
    )

    assert draft.should_write_memory is False
    assert {item.field for item in draft.recommendations} >= {"session_summary", "active_intent", "next_action", "verification"}
    assert not memory_path.exists()


def test_accept_handoff_draft_field_records_provenance_and_allows_undo(tmp_path: Path) -> None:
    memory_path = tmp_path / ".vibelign" / "work_memory.json"
    save_memory_state(memory_path, MemoryState(active_intent=MemoryTextField(text="Old intent", source="explicit")))
    draft = build_handoff_summary_draft(memory_path, {"active_intent": "New reviewed intent"})

    result = accept_handoff_draft_field(memory_path, draft, "active_intent", accepted_by="tester")
    state = load_memory_state(memory_path)

    assert result.ok is True
    assert state.active_intent is not None
    assert state.active_intent.text == "New reviewed intent"
    assert state.active_intent.source == "llm_proposed"
    assert state.active_intent.accepted_by == "tester"
    assert state.unknown_fields["recently_accepted_proposals"]

    undo = undo_recent_handoff_acceptance(memory_path, result.proposal_hash, undone_by="tester")
    restored = load_memory_state(memory_path)
    assert undo.ok is True
    assert restored.active_intent is not None
    assert restored.active_intent.text == "Old intent"


def test_dismiss_handoff_draft_field_suppresses_equivalent_proposal(tmp_path: Path) -> None:
    memory_path = tmp_path / ".vibelign" / "work_memory.json"
    draft = build_handoff_summary_draft(memory_path, {"first_next_action": "Review draft"})

    result = dismiss_handoff_draft_field(memory_path, draft, "next_action")
    repeated = build_handoff_summary_draft(memory_path, {"first_next_action": "Review draft"})

    assert result.ok is True
    assert not [item for item in repeated.recommendations if item.field == "next_action"]


def test_handoff_draft_payload_is_stable_json_shape(tmp_path: Path) -> None:
    draft = build_handoff_summary_draft(
        tmp_path / ".vibelign" / "work_memory.json",
        {"session_summary": "Reviewable handoff"},
    )
    payload = handoff_draft_to_payload(draft)

    assert payload["draft_id"]
    assert payload["should_write_memory"] is False
    assert "recommendations" in payload


def test_transfer_handoff_ai_non_interactive_writes_context_and_prints_draft_json(tmp_path: Path, capsys) -> None:
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = argparse.Namespace(
        compact=False,
        full=False,
        handoff=True,
        ai=True,
        no_prompt=True,
        print_mode=False,
        dry_run=False,
        out=str(out_path),
        session_summary="AI draft handoff",
        first_next_action="Review proposals",
        verification=None,
        decision=None,
    )

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["deterministic_handoff_written"] is True
    assert payload["draft"]["should_write_memory"] is False
    assert out_path.exists()
    assert "AI draft handoff" in out_path.read_text(encoding="utf-8")
    state = load_memory_state(tmp_path / ".vibelign" / "work_memory.json")
    assert state.next_action is None


def test_accept_session_summary_records_observed_handoff_context(tmp_path: Path) -> None:
    memory_path = tmp_path / ".vibelign" / "work_memory.json"
    draft = build_handoff_summary_draft(memory_path, {"session_summary": "Summarize reviewed handoff"})

    result = accept_handoff_draft_field(memory_path, draft, "session_summary", accepted_by="tester")
    state = load_memory_state(memory_path)

    assert result.ok is True
    assert state.observed_context[-1].kind == "handoff_summary"
    assert state.observed_context[-1].summary == "Summarize reviewed handoff"
    assert state.observed_context[-1].source_tool == "tester"


def test_undo_session_summary_preserves_prior_observed_context(tmp_path: Path) -> None:
    memory_path = tmp_path / ".vibelign" / "work_memory.json"
    save_memory_state(
        memory_path,
        MemoryState(
            observed_context=[
                MemoryObservedContext(
                    kind="modified",
                    summary="existing context",
                    path="src/app.py",
                    timestamp="2026-05-05T00:00:00Z",
                    source_tool="watch",
                )
            ]
        ),
    )
    draft = build_handoff_summary_draft(memory_path, {"session_summary": "Temporary summary"})

    accepted = accept_handoff_draft_field(memory_path, draft, "session_summary", accepted_by="tester")
    after_accept = load_memory_state(memory_path)
    assert len(after_accept.observed_context) == 2

    undo = undo_recent_handoff_acceptance(memory_path, accepted.proposal_hash, undone_by="tester")
    restored = load_memory_state(memory_path)

    assert undo.ok is True
    assert len(restored.observed_context) == 1
    assert restored.observed_context[0].summary == "existing context"
    assert restored.observed_context[0].path == "src/app.py"


def test_undo_restores_list_based_handoff_proposal_fields(tmp_path: Path) -> None:
    memory_path = tmp_path / ".vibelign" / "work_memory.json"
    draft = build_handoff_summary_draft(
        memory_path,
        {
            "relevant_files": [{"path": "src/app.py", "why": "reviewed file"}],
            "verification": ["pytest tests/test_memory_agent.py -> passed"],
            "warnings": ["Review risky generated output"],
        },
    )

    results = [
        accept_handoff_draft_field(memory_path, draft, "relevant_files", accepted_by="tester"),
        accept_handoff_draft_field(memory_path, draft, "verification", accepted_by="tester"),
        accept_handoff_draft_field(memory_path, draft, "risk_notes", accepted_by="tester"),
    ]
    accepted = load_memory_state(memory_path)
    assert accepted.relevant_files
    assert accepted.verification
    assert accepted.risks

    for result in reversed(results):
        undo = undo_recent_handoff_acceptance(memory_path, result.proposal_hash, undone_by="tester")
        assert undo.ok is True

    restored = load_memory_state(memory_path)
    assert restored.relevant_files == []
    assert restored.verification == []
    assert restored.risks == []
