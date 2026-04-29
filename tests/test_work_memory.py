import json
from pathlib import Path

from vibelign.core.work_memory import (
    MAX_RECENT_EVENTS,
    MAX_RELEVANT_FILES,
    add_decision,
    add_verification,
    build_transfer_summary,
    load_work_memory,
    record_event,
    record_warning,
    save_work_memory,
)


def test_load_missing_file_returns_default_state(tmp_path: Path) -> None:
    state = load_work_memory(tmp_path / ".vibelign" / "work_memory.json")
    assert state["schema_version"] == 1
    assert state["recent_events"] == []
    assert state["relevant_files"] == []
    assert state["warnings"] == []


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    state = load_work_memory(path)
    state["verification"] = ["uv run pytest tests/test_work_memory.py"]
    save_work_memory(path, state)

    loaded = load_work_memory(path)
    assert loaded["verification"] == ["uv run pytest tests/test_work_memory.py"]


def test_record_event_updates_updated_at(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_event(path, kind="modified", rel_path="src/app.py", message="changed app")

    loaded = load_work_memory(path)
    assert loaded["updated_at"]
    assert loaded["recent_events"][-1].get("path") == "src/app.py"


def test_pruning_caps_lists(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    for index in range(MAX_RECENT_EVENTS + 5):
        record_event(
            path,
            kind="modified",
            rel_path=f"src/file_{index}.py",
            message=f"file {index}",
        )
    for index in range(MAX_RELEVANT_FILES + 5):
        record_warning(
            path,
            rel_path=f"src/warn_{index}.py",
            message=f"warn {index}",
            action="check it",
        )

    loaded = load_work_memory(path)
    assert len(loaded["recent_events"]) == MAX_RECENT_EVENTS
    assert len(loaded["relevant_files"]) == MAX_RELEVANT_FILES
    assert loaded["recent_events"][0].get("path") == "src/file_20.py"


def test_long_text_truncation_works(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    long_text = "x" * 1000
    record_warning(path, rel_path="src/app.py", message=long_text, action=long_text)

    loaded = load_work_memory(path)
    warning = loaded["warnings"][-1]
    assert len(warning.get("message", "")) <= 400
    assert warning.get("message", "").endswith("…")
    assert len(warning.get("action", "")) <= 400


def test_transfer_summary_uses_compact_work_memory_facts(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_event(
        path,
        kind="created",
        rel_path="src/new_module.py",
        message="src/new_module.py created",
        action="Open the new module and verify imports.",
    )
    summary = build_transfer_summary(path)

    assert summary is not None
    assert "src/new_module.py" in summary.get("changed_files", [])
    assert "현재 세션" in summary.get("session_summary", "")
    assert "src/new_module.py" in summary.get("session_summary", "")
    assert summary.get("first_next_action") == "Open the new module and verify imports."
    assert summary.get("concrete_next_steps") == ["Open the new module and verify imports."]
    assert summary.get("state_references") == [".vibelign/work_memory.json"]


def test_transfer_summary_uses_latest_decision_as_active_intent(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    add_decision(path, "Improve current-session handoff continuation quality.")
    add_decision(path, "Surface active intent and verification in transfer handoff.")

    summary = build_transfer_summary(path)

    assert summary is not None
    assert summary.get("active_intent") == "Surface active intent and verification in transfer handoff."


def test_transfer_summary_deduplicates_recent_lines(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_event(path, kind="modified", rel_path="src/app.py", message="src/app.py modified")
    record_event(path, kind="modified", rel_path="src/app.py", message="src/app.py modified")
    record_warning(path, rel_path="src/app.py", message="app.py에 앵커가 없습니다")
    record_warning(path, rel_path="src/app.py", message="app.py에 앵커가 없습니다")

    summary = build_transfer_summary(path)

    assert summary is not None
    assert summary.get("recent_events", []).count(
        "modified: src/app.py — src/app.py modified"
    ) == 1
    assert summary.get("warnings", []).count("src/app.py — app.py에 앵커가 없습니다") == 1


def test_transfer_summary_preserves_warning_action(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_warning(
        path,
        rel_path="src/app.py",
        message="app.py에 앵커가 없습니다",
        action="vib doctor --fix-anchors --paths src/app.py",
    )

    summary = build_transfer_summary(path)

    assert summary is not None
    warnings = summary.get("warnings", [])
    assert warnings == [
        "src/app.py — app.py에 앵커가 없습니다 → vib doctor --fix-anchors --paths src/app.py"
    ]


def test_record_event_skips_unsafe_absolute_paths(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_event(path, kind="modified", rel_path="/Users/me/secret.py", message="secret")

    loaded = load_work_memory(path)
    assert loaded["recent_events"] == []


def test_record_event_skips_generated_artifact_paths(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_event(
        path,
        kind="modified",
        rel_path="vibelign.egg-info/PKG-INFO",
        message="PKG-INFO modified",
    )

    loaded = load_work_memory(path)
    assert loaded["recent_events"] == []
    assert loaded["relevant_files"] == []


def test_record_event_skips_omc_agent_state_paths(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_event(
        path,
        kind="modified",
        rel_path=".omc/state/subagent-tracker.lock",
        message="agent state noise",
    )

    loaded = load_work_memory(path)
    assert loaded["recent_events"] == []
    assert loaded["relevant_files"] == []


def test_add_verification_replaces_same_command_result(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    add_verification(path, "uv run pytest tests/test_work_memory.py -> 12 passed")
    add_verification(path, "uv run pytest tests/test_work_memory.py -> 13 passed")

    loaded = load_work_memory(path)
    assert loaded["verification"] == [
        "uv run pytest tests/test_work_memory.py -> 13 passed"
    ]


def test_add_verification_replaces_long_py_compile_command(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    add_verification(
        path,
        "uv run python -m py_compile a.py b.py c.py -> success",
    )
    add_verification(
        path,
        "uv run python -m py_compile a.py b.py c.py d.py -> success",
    )

    loaded = load_work_memory(path)
    assert loaded["verification"] == [
        "uv run python -m py_compile a.py b.py c.py d.py -> success"
    ]


def test_load_work_memory_prunes_stale_generated_artifact_paths(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-04-26T00:00:00Z",
                "recent_events": [
                    {
                        "kind": "modified",
                        "path": "vibelign.egg-info/SOURCES.txt",
                        "message": "SOURCES.txt modified",
                    },
                    {
                        "kind": "modified",
                        "path": ".omc/project-memory.json",
                        "message": "agent state noise",
                    },
                    {
                        "kind": "modified",
                        "path": "src/app.py",
                        "message": "src/app.py modified",
                    },
                ],
                "relevant_files": [
                    {"path": "vibelign.egg-info/PKG-INFO", "why": "Generated."},
                    {"path": ".omc/state/subagent-tracker.lock", "why": "Agent state."},
                    {"path": "src/app.py", "why": "Source file."},
                ],
                "warnings": [
                    {
                        "kind": "warning",
                        "path": ".omc/project-memory.json",
                        "message": "project-memory.json에 앵커가 없습니다",
                    },
                    {
                        "kind": "warning",
                        "path": "vibelign.egg-info/PKG-INFO",
                        "message": "PKG-INFO에 앵커가 없습니다",
                    }
                ],
                "decisions": [],
                "verification": [],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_work_memory(path)
    assert [event.get("path") for event in loaded["recent_events"]] == ["src/app.py"]
    assert loaded["relevant_files"] == [
        {"path": "src/app.py", "why": "Source file.", "source": "watch"}
    ]
    assert loaded["warnings"] == []


def test_record_warning_skips_parent_traversal_paths(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    record_warning(path, rel_path="../secret.py", message="secret")

    loaded = load_work_memory(path)
    assert loaded["warnings"] == []
