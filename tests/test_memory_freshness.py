from importlib import import_module
from typing import Callable, Protocol, cast

from vibelign.core.memory.models import (
    MemoryObservedContext,
    MemoryRelevantFile,
    MemoryState,
    MemoryTextField,
    MemoryVerification,
)


class _MemoryFreshnessLike(Protocol):
    verification_freshness: str
    stale_verification_commands: list[str]
    stale_intent: bool
    stale_relevant_files: list[str]
    conflicting_fields: list[str]
    missing_next_action: bool
    missing_decision_after_patches: bool
    active_trigger_ids: list[str]


def _assess_memory_freshness() -> Callable[[MemoryState], _MemoryFreshnessLike]:
    module = import_module("vibelign.core.memory.freshness")
    return cast(
        Callable[[MemoryState], _MemoryFreshnessLike],
        getattr(module, "assess_memory_freshness"),
    )


def test_assess_memory_freshness_reports_stale_metadata() -> None:
    state = MemoryState(
        active_intent=MemoryTextField(text="Old goal", stale=True),
        next_action=MemoryTextField(text="Old action"),
        relevant_files=[
            MemoryRelevantFile(path="src/app.py", why="old file", stale=True),
            MemoryRelevantFile(
                path="src/previous.py",
                why="previous intent file",
                from_previous_intent=True,
            ),
            MemoryRelevantFile(path="src/current.py", why="fresh file"),
        ],
        verification=[
            MemoryVerification(command="uv run python -m pytest tests/test_old.py", stale=True),
            MemoryVerification(command="uv run python -m pytest tests/test_current.py"),
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == "stale"
    assert freshness.stale_verification_commands == [
        "uv run python -m pytest tests/test_old.py"
    ]
    assert freshness.stale_intent is True
    assert freshness.stale_relevant_files == ["src/app.py", "src/previous.py"]
    assert freshness.active_trigger_ids == [
        "stale_verification",
        "stale_intent",
        "stale_relevant_files",
    ]


def test_assess_memory_freshness_marks_old_intent_stale() -> None:
    state = MemoryState(
        active_intent=MemoryTextField(
            text="Old goal",
            last_updated="2026-05-01T00:00:00Z",
        )
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.stale_intent is True


def test_assess_memory_freshness_marks_intent_stale_after_many_commits() -> None:
    state = MemoryState(
        active_intent=MemoryTextField(
            text="Goal before commits",
            last_updated="2999-01-01T00:00:00Z",
        ),
        observed_context=[
            MemoryObservedContext(
                kind="commit",
                summary=f"commit {index}",
                timestamp=f"2999-01-01T00:0{index + 1}:00Z",
            )
            for index in range(5)
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.stale_intent is True


def test_assess_memory_freshness_reports_empty_for_fresh_memory() -> None:
    state = MemoryState(
        active_intent=MemoryTextField(text="Fresh goal"),
        verification=[MemoryVerification(command="uv run python -m pytest tests/test_current.py")],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == ""
    assert freshness.stale_verification_commands == []


def test_assess_memory_freshness_detects_same_field_conflicts() -> None:
    state = MemoryState(
        next_action=MemoryTextField(text="Continue handoff"),
        decisions=[
            MemoryTextField(text="Use A", last_updated="2026-05-03T00:00:00Z"),
            MemoryTextField(text="Use B", last_updated="2026-05-03T00:00:30Z"),
        ],
        observed_context=[
            MemoryObservedContext(
                kind="modified",
                summary="first",
                timestamp="2026-05-03T00:10:00Z",
            ),
            MemoryObservedContext(
                kind="modified",
                summary="second",
                timestamp="2026-05-03T00:10:45Z",
            ),
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.conflicting_fields == ["decisions", "observed_context"]
    assert "conflict_detected" in freshness.active_trigger_ids


def test_assess_memory_freshness_ignores_conflicts_outside_window() -> None:
    state = MemoryState(
        next_action=MemoryTextField(text="Continue handoff"),
        decisions=[
            MemoryTextField(text="Use A", last_updated="2026-05-03T00:00:00Z"),
            MemoryTextField(text="Use B", last_updated="2026-05-03T00:02:01Z"),
        ],
        verification=[
            MemoryVerification(command="pytest a", last_updated="2026-05-03T00:00:00Z"),
            MemoryVerification(command="pytest b", last_updated="2026-05-03T00:01:01Z"),
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.conflicting_fields == []
    assert freshness.missing_next_action is False
    assert "conflict_detected" not in freshness.active_trigger_ids
    assert freshness.stale_intent is False
    assert freshness.stale_relevant_files == []
    assert freshness.active_trigger_ids == []


def test_assess_memory_freshness_marks_verification_stale_when_related_file_changes() -> None:
    state = MemoryState(
        verification=[
            MemoryVerification(
                command="uv run pytest tests/test_app.py",
                last_updated="2026-05-03T00:00:00Z",
                related_files=["src/app.py"],
            ),
            MemoryVerification(
                command="uv run pytest tests/test_other.py",
                last_updated="2026-05-03T00:05:00Z",
                related_files=["src/other.py"],
            ),
        ],
        observed_context=[
            MemoryObservedContext(
                kind="modified",
                summary="app changed after verification",
                path="src/app.py",
                timestamp="2026-05-03T00:10:00Z",
            ),
            MemoryObservedContext(
                kind="modified",
                summary="other changed before verification",
                path="src/other.py",
                timestamp="2026-05-03T00:04:00Z",
            ),
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == "stale"
    assert freshness.stale_verification_commands == ["uv run pytest tests/test_app.py"]


def test_assess_memory_freshness_ignores_scope_unknown_without_timestamp() -> None:
    state = MemoryState(
        verification=[MemoryVerification(command="uv run pytest", last_updated="")],
        observed_context=[
            MemoryObservedContext(
                kind="modified",
                summary="changed",
                path="src/app.py",
                timestamp="2026-05-03T00:10:00Z",
            )
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == ""
    assert freshness.stale_verification_commands == []


def test_assess_memory_freshness_marks_missing_next_action_trigger() -> None:
    state = MemoryState(active_intent=MemoryTextField(text="Prepare handoff"))

    freshness = _assess_memory_freshness()(state)

    assert freshness.missing_next_action is True
    assert "missing_next_action" in freshness.active_trigger_ids


def test_assess_memory_freshness_marks_missing_decision_after_repeated_patches() -> None:
    state = MemoryState(
        next_action=MemoryTextField(text="Continue handoff"),
        relevant_files=[
            MemoryRelevantFile(
                path=f"src/file_{index}.py",
                why="patch_apply target",
                source="observed",
                updated_by="mcp patch_apply",
            )
            for index in range(3)
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.missing_decision_after_patches is True
    assert "missing_decision_after_patches" in freshness.active_trigger_ids


def test_assess_memory_freshness_skips_patch_decision_trigger_when_decision_exists() -> None:
    state = MemoryState(
        decisions=[MemoryTextField(text="Keep patch path")],
        next_action=MemoryTextField(text="Continue handoff"),
        relevant_files=[
            MemoryRelevantFile(
                path=f"src/file_{index}.py",
                why="patch_apply target",
                source="observed",
                updated_by="mcp patch_apply",
            )
            for index in range(3)
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.missing_decision_after_patches is False
    assert "missing_decision_after_patches" not in freshness.active_trigger_ids


def test_assess_memory_freshness_marks_scope_unknown_verification_stale() -> None:
    state = MemoryState(
        verification=[
            MemoryVerification(
                command="uv run pytest tests/test_memory_freshness.py",
                scope_unknown=True,
            )
        ]
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == "stale"
    assert freshness.stale_verification_commands == [
        "uv run pytest tests/test_memory_freshness.py"
    ]
    assert "stale_verification" in freshness.active_trigger_ids


def test_assess_memory_freshness_marks_verification_stale_when_newer_patch_exists() -> None:
    state = MemoryState(
        next_action=MemoryTextField(text="Continue handoff"),
        verification=[
            MemoryVerification(
                command="uv run pytest tests/test_app.py",
                last_updated="2026-05-03T00:00:00Z",
                related_files=["src/app.py"],
            )
        ],
        relevant_files=[
            MemoryRelevantFile(
                path="src/other.py",
                why="patch_apply target",
                source="observed",
                last_updated="2026-05-03T00:10:00Z",
                updated_by="mcp patch_apply",
            )
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == "stale"
    assert freshness.stale_verification_commands == ["uv run pytest tests/test_app.py"]
    assert "stale_verification" in freshness.active_trigger_ids


def test_assess_memory_freshness_marks_verification_stale_after_intent_change() -> None:
    state = MemoryState(
        active_intent=MemoryTextField(
            text="New goal",
            last_updated="2026-05-03T00:10:00Z",
        ),
        next_action=MemoryTextField(text="Continue handoff"),
        verification=[
            MemoryVerification(
                command="uv run pytest tests/test_app.py",
                last_updated="2026-05-03T00:00:00Z",
                related_files=["src/app.py"],
            )
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == "stale"
    assert freshness.stale_verification_commands == ["uv run pytest tests/test_app.py"]
    assert "stale_verification" in freshness.active_trigger_ids


def test_assess_memory_freshness_keeps_verification_fresh_when_intent_is_older() -> None:
    state = MemoryState(
        active_intent=MemoryTextField(
            text="Existing goal",
            last_updated="2026-05-03T00:00:00Z",
        ),
        next_action=MemoryTextField(text="Continue handoff"),
        verification=[
            MemoryVerification(
                command="uv run pytest tests/test_app.py",
                last_updated="2026-05-03T00:10:00Z",
                related_files=["src/app.py"],
            )
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == ""
    assert freshness.stale_verification_commands == []
    assert "stale_verification" not in freshness.active_trigger_ids


def test_assess_memory_freshness_ignores_patch_before_verification() -> None:
    state = MemoryState(
        next_action=MemoryTextField(text="Continue handoff"),
        verification=[
            MemoryVerification(
                command="uv run pytest tests/test_app.py",
                last_updated="2026-05-03T00:10:00Z",
                related_files=["src/app.py"],
            )
        ],
        relevant_files=[
            MemoryRelevantFile(
                path="src/other.py",
                why="patch_apply target",
                source="observed",
                last_updated="2026-05-03T00:00:00Z",
                updated_by="mcp patch_apply",
            )
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == ""
    assert freshness.stale_verification_commands == []
    assert "stale_verification" not in freshness.active_trigger_ids


def test_assess_memory_freshness_ignores_unrelated_file_changes_after_verification() -> None:
    state = MemoryState(
        verification=[
            MemoryVerification(
                command="uv run pytest tests/test_app.py",
                last_updated="2026-05-03T00:00:00Z",
                related_files=["src/app.py"],
            )
        ],
        observed_context=[
            MemoryObservedContext(
                kind="modified",
                summary="unrelated file changed after verification",
                path="src/other.py",
                timestamp="2026-05-03T00:10:00Z",
            )
        ],
    )

    freshness = _assess_memory_freshness()(state)

    assert freshness.verification_freshness == ""
    assert freshness.stale_verification_commands == []
