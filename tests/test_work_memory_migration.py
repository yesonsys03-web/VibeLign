import json
from pathlib import Path

from vibelign.core.memory.models import (
    MemoryObservedContext,
    MemoryRelevantFile,
    MemoryState,
    MemoryTextField,
    MemoryVerification,
)
from vibelign.core.memory.store import (
    add_memory_decision,
    build_handoff_summary,
    load_memory_state,
    save_memory_state,
    set_memory_active_intent,
)


def test_legacy_decisions_migrate_without_data_loss(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-05-02T00:00:00Z",
                "decisions": ["Keep recovery read-only", "Build memory core next"],
                "relevant_files": [
                    {"path": "vibelign/core/memory/store.py", "why": "new store", "source": "explicit"}
                ],
                "recent_events": [
                    {"kind": "modified", "path": "vibelign/core/memory/store.py", "message": "store added"}
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert [decision.text for decision in state.decisions] == [
        "Keep recovery read-only",
        "Build memory core next",
    ]
    assert state.active_intent is not None
    assert state.active_intent.text == "Build memory core next"
    assert state.active_intent.proposed is True
    assert state.relevant_files[0].source == "explicit"
    assert state.observed_context[0].kind == "modified"
    assert "updated_at" not in state.unknown_fields
    assert "recent_events" not in state.unknown_fields


def test_legacy_next_action_migrates_to_handoff_summary(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-05-02T00:00:00Z",
                "next_action": "Review explicit handoff next step",
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)
    summary = build_handoff_summary(path)

    assert state.next_action is not None
    assert state.next_action.text == "Review explicit handoff next step"
    assert summary is not None
    assert summary.get("first_next_action") == "Review explicit handoff next step"
    assert summary.get("concrete_next_steps") == ["Review explicit handoff next step"]


def test_current_schema_typed_memory_state_loads_without_legacy_loss(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {
                    "text": "Keep typed memory structured",
                    "last_updated": "2026-05-02T00:00:00Z",
                    "updated_by": "vib memory review",
                    "source": "explicit",
                    "proposed": True,
                },
                "decisions": [
                    {
                        "text": "Use typed parser before MCP",
                        "source": "explicit",
                    }
                ],
                "relevant_files": [
                    {
                        "path": "vibelign/core/memory/store.py",
                        "why": "typed parser",
                        "source": "explicit",
                        "stale": True,
                    }
                ],
                "verification": [
                    {
                        "command": "uv run python -m pytest tests/test_work_memory_migration.py",
                        "result": "passed",
                        "related_files": ["tests/test_work_memory_migration.py"],
                        "stale": False,
                    }
                ],
                "risks": [
                    {"text": "Do not parse commands from free text", "source": "system"}
                ],
                "next_action": {
                    "text": "Run typed parser QA",
                    "source": "explicit",
                },
                "observed_context": [
                    {
                        "kind": "modified",
                        "summary": "store parser changed",
                        "path": "vibelign/core/memory/store.py",
                        "source_tool": "test",
                    }
                ],
                "archived_decisions": [
                    {"text": "Old decision", "from_previous_intent": True}
                ],
                "future_field": {"keep": True},
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)
    summary = build_handoff_summary(path)

    assert state.active_intent is not None
    assert state.active_intent.text == "Keep typed memory structured"
    assert state.active_intent.updated_by == "vib memory review"
    assert state.active_intent.proposed is True
    assert state.decisions[0].text == "Use typed parser before MCP"
    assert state.relevant_files[0].path == "vibelign/core/memory/store.py"
    assert state.relevant_files[0].source == "explicit"
    assert state.relevant_files[0].stale is True
    assert state.verification[0].command == "uv run python -m pytest tests/test_work_memory_migration.py"
    assert state.verification[0].result == "passed"
    assert state.verification[0].related_files == ["tests/test_work_memory_migration.py"]
    assert state.risks[0].source == "system"
    assert state.next_action is not None
    assert state.next_action.text == "Run typed parser QA"
    assert state.observed_context[0].source_tool == "test"
    assert state.archived_decisions[0].from_previous_intent is True
    assert state.unknown_fields == {"future_field": {"keep": True}}
    assert summary is not None
    assert summary.get("active_intent") == "Keep typed memory structured"
    assert summary.get("first_next_action") == "Run typed parser QA"
    assert summary.get("verification") == [
        "uv run python -m pytest tests/test_work_memory_migration.py -> passed"
    ]


def test_current_schema_typed_reader_rejects_unsafe_paths(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "relevant_files": [
                    {"path": "/tmp/secret.py", "why": "absolute", "source": "explicit"},
                    {"path": "safe/file.py", "why": "safe", "source": "explicit"},
                ],
                "verification": [
                    {
                        "command": "pytest",
                        "related_files": ["C:/Users/name/secret.py", "tests/test_safe.py"],
                    }
                ],
                "observed_context": [
                    {"kind": "modified", "summary": "unsafe", "path": "../secret.py"},
                    {"kind": "modified", "summary": "safe", "path": "safe/file.py"},
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert [item.path for item in state.relevant_files] == ["safe/file.py"]
    assert state.verification[0].related_files == ["tests/test_safe.py"]
    assert [item.path for item in state.observed_context] == ["safe/file.py"]


def test_current_schema_relevant_files_only_preserves_typed_metadata(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "relevant_files": [
                    {
                        "path": "vibelign/core/memory/store.py",
                        "why": "typed relevant metadata",
                        "source": "observed",
                        "last_updated": "2026-05-02T00:00:00Z",
                        "updated_by": "memory-review",
                        "stale": True,
                        "from_previous_intent": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert len(state.relevant_files) == 1
    relevant = state.relevant_files[0]
    assert relevant.path == "vibelign/core/memory/store.py"
    assert relevant.why == "typed relevant metadata"
    assert relevant.source == "observed"
    assert relevant.last_updated == "2026-05-02T00:00:00Z"
    assert relevant.updated_by == "memory-review"
    assert relevant.stale is True
    assert relevant.from_previous_intent is True


def test_memory_compaction_archives_old_decisions_without_changing_active_intent(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    decisions = [
        {"text": f"Decision {index:02d}", "source": "explicit"}
        for index in range(55)
    ]
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {
                    "text": "Pinned active intent",
                    "source": "explicit",
                },
                "decisions": decisions,
                "archived_decisions": [
                    {"text": "Previously archived", "source": "explicit"}
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert state.active_intent is not None
    assert state.active_intent.text == "Pinned active intent"
    assert len(state.decisions) == 50
    assert state.decisions[0].text == "Decision 05"
    assert state.decisions[-1].text == "Decision 54"
    assert [item.text for item in state.archived_decisions[:6]] == [
        "Previously archived",
        "Decision 00",
        "Decision 01",
        "Decision 02",
        "Decision 03",
        "Decision 04",
    ]


def test_memory_compaction_caps_relevant_files_and_observed_context(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    save_memory_state(
        path,
        MemoryState(
            relevant_files=[
                MemoryRelevantFile(path=f"src/file_{index:03d}.py", why="cap test")
                for index in range(105)
            ],
            observed_context=[
                MemoryObservedContext(kind="modified", summary=f"event {index}")
                for index in range(205)
            ],
        ),
    )

    state = load_memory_state(path)

    assert len(state.relevant_files) == 100
    assert state.relevant_files[0].path == "src/file_005.py"
    assert state.relevant_files[-1].path == "src/file_104.py"
    assert len(state.observed_context) == 200
    assert state.observed_context[0].summary == "event 5"
    assert state.observed_context[-1].summary == "event 204"


def test_memory_compaction_caps_verification_per_scope(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    save_memory_state(
        path,
        MemoryState(
            verification=[
                MemoryVerification(
                    command=f"pytest tests/test_a.py::{index}",
                    related_files=["tests/test_a.py"],
                )
                for index in range(35)
            ]
            + [
                MemoryVerification(
                    command=f"pytest tests/test_b.py::{index}",
                    related_files=["tests/test_b.py"],
                )
                for index in range(32)
            ]
            + [
                MemoryVerification(command=f"pytest unknown::{index}")
                for index in range(31)
            ],
        ),
    )

    state = load_memory_state(path)

    assert len([item for item in state.verification if item.related_files == ["tests/test_a.py"]]) == 30
    assert len([item for item in state.verification if item.related_files == ["tests/test_b.py"]]) == 30
    assert len([item for item in state.verification if not item.related_files]) == 30
    assert state.verification[0].command == "pytest tests/test_a.py::5"
    assert state.verification[-1].command == "pytest unknown::30"


def test_memory_compaction_canonicalizes_multi_file_verification_scope(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    save_memory_state(
        path,
        MemoryState(
            verification=[
                MemoryVerification(
                    command=f"pytest multi::{index}",
                    related_files=["tests/test_a.py", "tests/test_b.py"]
                    if index % 2 == 0
                    else ["tests/test_b.py", "tests/test_a.py"],
                )
                for index in range(35)
            ],
        ),
    )

    state = load_memory_state(path)

    assert len(state.verification) == 30
    assert state.verification[0].command == "pytest multi::5"
    assert state.verification[-1].command == "pytest multi::34"
    assert all(item.from_previous_intent for item in state.archived_decisions[1:6])


def test_memory_compaction_infers_active_intent_before_archiving(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "decisions": [
                    {"text": f"Decision {index:02d}", "source": "explicit"}
                    for index in range(55)
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert state.active_intent is not None
    assert state.active_intent.text == "Decision 54"
    assert state.active_intent.proposed is True
    assert len(state.decisions) == 50
    assert state.archived_decisions[0].text == "Decision 00"


def test_memory_compaction_leaves_exactly_fifty_decisions_unchanged(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "decisions": [
                    {"text": f"Decision {index:02d}", "source": "explicit"}
                    for index in range(50)
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert len(state.decisions) == 50
    assert state.decisions[0].text == "Decision 00"
    assert state.archived_decisions == []


def test_memory_compaction_is_idempotent_for_compacted_state() -> None:
    from vibelign.core.memory.store import compact_memory_state

    state = load_memory_state(_write_compaction_fixture_decisions(55))

    compacted_again = compact_memory_state(state)

    assert [item.text for item in compacted_again.archived_decisions] == [
        item.text for item in state.archived_decisions
    ]
    assert [item.text for item in compacted_again.decisions] == [
        item.text for item in state.decisions
    ]


def test_save_memory_state_round_trips_typed_fields_and_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    state = MemoryState(
        active_intent=MemoryTextField(text="Save typed memory", source="explicit"),
        decisions=[MemoryTextField(text="Typed decision", source="explicit")],
        next_action=MemoryTextField(text="Reload typed memory", source="explicit"),
        unknown_fields={"future_field": {"keep": True}},
    )

    save_memory_state(path, state)
    loaded = load_memory_state(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert raw["schema_version"] == 1
    assert raw["future_field"] == {"keep": True}
    assert loaded.active_intent is not None
    assert loaded.active_intent.text == "Save typed memory"
    assert loaded.decisions[0].text == "Typed decision"
    assert loaded.next_action is not None
    assert loaded.next_action.text == "Reload typed memory"
    assert loaded.unknown_fields == {"future_field": {"keep": True}}


def test_save_memory_state_compacts_decisions_before_write(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    state = MemoryState(
        active_intent=MemoryTextField(text="Pinned active intent", source="explicit"),
        decisions=[
            MemoryTextField(text=f"Decision {index:02d}", source="explicit")
            for index in range(55)
        ],
    )

    save_memory_state(path, state)
    loaded = load_memory_state(path)

    assert loaded.active_intent is not None
    assert loaded.active_intent.text == "Pinned active intent"
    assert len(loaded.decisions) == 50
    assert loaded.decisions[0].text == "Decision 05"
    assert len(loaded.archived_decisions) == 5
    assert loaded.archived_decisions[0].text == "Decision 00"
    assert loaded.archived_decisions[0].from_previous_intent is True


def test_save_memory_state_refuses_read_only_state(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    state = MemoryState(read_only=True)

    try:
        save_memory_state(path, state)
    except ValueError as exc:
        assert "refusing to write" in str(exc)
    else:
        raise AssertionError("save_memory_state should refuse read-only memory")
    assert not path.exists()


def test_save_memory_state_refuses_future_schema_without_touching_file(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    original = '{"schema_version": 1, "decisions": []}\n'
    path.write_text(original, encoding="utf-8")
    state = MemoryState(schema_version=99, decisions=[MemoryTextField(text="Do not write")])

    try:
        save_memory_state(path, state)
    except ValueError as exc:
        assert "refusing to write" in str(exc)
    else:
        raise AssertionError("save_memory_state should refuse future schemas")
    assert path.read_text(encoding="utf-8") == original


def test_save_memory_state_typed_fields_override_unknown_field_collisions(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    state = MemoryState(
        active_intent=MemoryTextField(text="Canonical intent"),
        decisions=[MemoryTextField(text="Canonical decision")],
        unknown_fields={
            "active_intent": {"text": "Unknown intent"},
            "decisions": [{"text": "Unknown decision"}],
            "future_field": True,
        },
    )

    save_memory_state(path, state)
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert raw["active_intent"]["text"] == "Canonical intent"
    assert raw["decisions"] == [
        {
            "text": "Canonical decision",
            "last_updated": "",
            "updated_by": "legacy_work_memory",
            "source": "legacy",
            "stale": False,
            "proposed": False,
            "from_previous_intent": False,
        }
    ]
    assert raw["future_field"] is True


def test_save_memory_state_does_not_emit_legacy_only_fields(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    state = MemoryState(
        decisions=[MemoryTextField(text="Typed decision")],
        unknown_fields={"updated_at": "legacy", "recent_events": ["legacy"]},
    )

    save_memory_state(path, state)
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert "updated_at" not in raw
    assert "recent_events" not in raw


def test_add_memory_decision_writes_typed_decision_and_proposed_intent(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"

    add_memory_decision(path, "Use typed decisions")
    state = load_memory_state(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    assert [item.text for item in state.decisions] == ["Use typed decisions"]
    assert state.decisions[0].source == "explicit"
    assert state.decisions[0].updated_by == "vib memory decide"
    assert state.decisions[0].last_updated
    assert state.active_intent is not None
    assert state.active_intent.text == "Use typed decisions"
    assert state.active_intent.proposed is True
    assert raw["decisions"][0]["text"] == "Use typed decisions"


def test_add_memory_decision_preserves_existing_active_intent(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    save_memory_state(
        path,
        MemoryState(active_intent=MemoryTextField(text="Pinned intent", source="explicit")),
    )

    add_memory_decision(path, "New decision")
    state = load_memory_state(path)

    assert state.active_intent is not None
    assert state.active_intent.text == "Pinned intent"
    assert [item.text for item in state.decisions] == ["New decision"]


def test_set_memory_active_intent_confirms_explicit_intent(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    add_memory_decision(path, "Proposed goal")

    set_memory_active_intent(path, "Confirmed goal")
    state = load_memory_state(path)

    assert state.active_intent is not None
    assert state.active_intent.text == "Confirmed goal"
    assert state.active_intent.source == "explicit"
    assert state.active_intent.updated_by == "vib memory intent"
    assert state.active_intent.proposed is False
    assert [item.text for item in state.decisions] == ["Proposed goal"]


def test_add_memory_decision_dedupes_and_uses_compaction(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    save_memory_state(
        path,
        MemoryState(
            decisions=[
                MemoryTextField(text=f"Decision {index:02d}", source="explicit")
                for index in range(50)
            ]
        ),
    )

    add_memory_decision(path, "Decision 10")
    add_memory_decision(path, "Decision 50")
    state = load_memory_state(path)

    assert len(state.decisions) == 50
    assert state.decisions[-2].text == "Decision 10"
    assert state.decisions[-1].text == "Decision 50"
    assert state.archived_decisions[0].text == "Decision 00"


def test_set_memory_next_action_preserves_typed_decisions(tmp_path: Path) -> None:
    from vibelign.core.memory.store import set_memory_next_action

    path = tmp_path / ".vibelign" / "work_memory.json"
    add_memory_decision(path, "Keep typed decision")

    set_memory_next_action(path, "Review typed next action")
    state = load_memory_state(path)

    assert [item.text for item in state.decisions] == ["Keep typed decision"]
    assert state.next_action is not None
    assert state.next_action.text == "Review typed next action"
    assert state.next_action.source == "explicit"


def _write_compaction_fixture_decisions(count: int) -> Path:
    import tempfile

    root = Path(tempfile.mkdtemp(prefix="vibelign-compaction-test-"))
    path = root / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "decisions": [
                    {"text": f"Decision {index:02d}", "source": "explicit"}
                    for index in range(count)
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_legacy_verification_without_scope_is_marked_stale(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "verification_updated_at": "2026-05-02T01:00:00Z",
                "verification": ["uv run pytest tests/test_work_memory.py -> passed"],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert len(state.verification) == 1
    assert state.verification[0].scope_unknown is True
    assert state.verification[0].stale is True
    assert state.verification[0].last_updated == "2026-05-02T01:00:00Z"


def test_malformed_memory_uses_minimal_state(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text("{broken", encoding="utf-8")

    state = load_memory_state(path)

    assert state.decisions == []
    assert state.relevant_files == []
    assert state.observed_context == []


def test_newer_schema_is_read_only_and_surfaces_handoff_warning(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 99,
                "decisions": ["Future memory format"],
                "future_field": {"keep": True},
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)
    summary = build_handoff_summary(path)

    assert state.read_only is True
    assert state.unknown_fields == {"future_field": {"keep": True}}
    assert "schema_version=99" in state.downgrade_warning
    assert summary is not None
    assert any("schema_version=99" in warning for warning in summary.get("warnings", []))


def test_handoff_summary_uses_typed_stale_verification_metadata(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "verification": ["uv run pytest tests/test_work_memory.py -> passed"],
            }
        ),
        encoding="utf-8",
    )

    summary = build_handoff_summary(path)

    assert summary is not None
    verification = summary.get("verification", [])
    assert verification == [
        "uv run pytest tests/test_work_memory.py -> passed (stale: scope unknown)"
    ]


def test_memory_reader_rejects_windows_absolute_paths(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 99,
                "recent_events": [
                    {"kind": "modified", "path": "C:/Users/name/secret.py", "message": "secret"}
                ],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert state.observed_context == []
