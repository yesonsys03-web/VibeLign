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
    assert freshness.stale_intent is False
    assert freshness.stale_relevant_files == []


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
