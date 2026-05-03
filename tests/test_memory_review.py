import json
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast


class _MemoryReviewLike(Protocol):
    has_memory: bool
    active_intent: str
    next_action: str
    decisions: list[str]
    relevant_files: list[str]
    observed_context: list[str]
    verification: list[str]
    warnings: list[str]
    downgrade_warning: str
    redaction: object
    suggestions: list[str]
    active_trigger_ids: list[str]


def _review_memory() -> Callable[[Path], _MemoryReviewLike]:
    module = import_module("vibelign.core.memory.review")
    return cast(Callable[[Path], _MemoryReviewLike], getattr(module, "review_memory"))


def _snooze_memory_review_triggers() -> Callable[[list[str]], None]:
    module = import_module("vibelign.core.memory.review")
    return cast(Callable[[list[str]], None], getattr(module, "snooze_memory_review_triggers"))


def _dismiss_memory_review_triggers() -> Callable[[list[str]], None]:
    module = import_module("vibelign.core.memory.review")
    return cast(Callable[[list[str]], None], getattr(module, "dismiss_memory_review_triggers"))


def _get_memory_review_trigger_actions() -> Callable[[], list[object]]:
    module = import_module("vibelign.core.memory.review")
    return cast(Callable[[], list[object]], getattr(module, "get_memory_review_trigger_actions"))


def _clear_memory_review_trigger_snoozes() -> Callable[[], None]:
    module = import_module("vibelign.core.memory.review")
    return cast(Callable[[], None], getattr(module, "clear_memory_review_trigger_snoozes"))


def test_memory_review_empty_memory_suggests_decision(tmp_path: Path) -> None:
    review = _review_memory()(tmp_path / ".vibelign" / "work_memory.json")

    assert review.has_memory is False
    assert review.suggestions == ['Add a decision with: vib memory decide "..."']


def test_memory_review_surfaces_next_action_and_stale_verification(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "decisions": ["Keep memory review read-only"],
                "relevant_files": [
                    {"path": "vibelign/core/memory/review.py", "why": "review service", "source": "explicit"},
                    {"path": "scratch.py", "why": "watch only", "source": "watch"},
                ],
                "recent_events": [
                    {"kind": "modified", "path": "scratch.py", "message": "watch event"}
                ],
                "next_action": "Rerun memory review tests",
                "verification": ["uv run python -m pytest tests/test_memory_review.py -> passed"],
            }
        ),
        encoding="utf-8",
    )

    review = _review_memory()(path)

    assert review.has_memory is True
    assert review.active_intent == "Keep memory review read-only"
    assert review.next_action == "Rerun memory review tests"
    assert review.decisions == ["Keep memory review read-only"]
    assert review.relevant_files == [
        "vibelign/core/memory/review.py — review service"
    ]
    assert review.observed_context == ["modified: scratch.py — watch event"]
    assert review.verification == [
        "uv run python -m pytest tests/test_memory_review.py -> passed (stale: scope unknown)"
    ]
    expected_suggestion = (
        "Rerun stale verification: uv run python -m pytest tests/test_memory_review.py "
        "[trigger: stale_verification; Accept / Dismiss / Snooze]"
    )
    assert review.suggestions == [expected_suggestion]
    assert review.active_trigger_ids == ["stale_verification"]


def test_memory_review_surfaces_downgrade_warning(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps({"schema_version": 99, "future_field": True}),
        encoding="utf-8",
    )

    review = _review_memory()(path)

    assert review.has_memory is True
    assert "schema_version=99" in review.downgrade_warning
    assert any("schema_version=99" in warning for warning in review.warnings)


def test_memory_review_suggests_missing_explicit_fields(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "warnings": [
                    {"kind": "warning", "path": "src/app.py", "message": "manual review needed"}
                ],
            }
        ),
        encoding="utf-8",
    )

    review = _review_memory()(path)

    missing_next_action_suggestion = (
        "Capture the next handoff action with --first-next-action. "
        "[trigger: missing_next_action; Accept / Dismiss / Snooze]"
    )
    assert review.has_memory is True
    assert review.suggestions == [
        'Confirm the current goal with: vib memory decide "..."',
        missing_next_action_suggestion,
        "Review warnings before using this memory as handoff truth.",
    ]
    assert "missing_next_action" in review.active_trigger_ids


def test_memory_review_redacts_sensitive_text(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    secret_text = "tok" + "en=fixtureSecretValue1234"
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "decisions": [f"{secret_text} lives in /Users/alice/project"],
                "next_action": "Check 10.0.0.5 before handoff",
            }
        ),
        encoding="utf-8",
    )

    review = _review_memory()(path)

    rendered = "\n".join(review.decisions + [review.next_action])
    assert "fixtureSecretValue1234" not in rendered
    assert "/Users/alice" not in rendered
    assert "10.0.0.5" not in rendered
    assert int(getattr(review.redaction, "secret_hits", 0)) >= 1
    assert int(getattr(review.redaction, "privacy_hits", 0)) >= 2


def test_memory_review_uses_freshness_for_stale_intent_and_relevant_files(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {"text": "Old goal", "stale": True},
                "next_action": {"text": "Review freshness"},
                "relevant_files": [
                    {
                        "path": "src/app.py",
                        "why": "old relevant file",
                        "source": "explicit",
                        "stale": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    review = _review_memory()(path)

    stale_intent_suggestion = (
        "Review stale intent or next action before handoff. "
        "[trigger: stale_intent; Accept / Dismiss / Snooze]"
    )
    stale_relevant_files_suggestion = (
        "Review stale relevant files before handoff. "
        "[trigger: stale_relevant_files; Accept / Dismiss / Snooze]"
    )
    assert stale_intent_suggestion in review.suggestions
    assert stale_relevant_files_suggestion in review.suggestions


def test_memory_review_snoozes_trigger_for_current_session(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {"text": "Old goal", "stale": True},
                "next_action": {"text": "Review freshness"},
            }
        ),
        encoding="utf-8",
    )
    clear_snoozes = _clear_memory_review_trigger_snoozes()
    snooze = _snooze_memory_review_triggers()

    try:
        clear_snoozes()
        before = _review_memory()(path)
        snooze(["stale_intent"])
        after = _review_memory()(path)
    finally:
        clear_snoozes()

    assert "stale_intent" in before.active_trigger_ids
    assert any("[trigger: stale_intent;" in item for item in before.suggestions)
    assert "stale_intent" not in after.active_trigger_ids
    assert not any("[trigger: stale_intent;" in item for item in after.suggestions)


def test_memory_review_surfaces_conflict_trigger(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {"text": "Resolve memory conflict"},
                "next_action": {"text": "Review conflict"},
                "decisions": [
                    {"text": "Use A", "last_updated": "2026-05-03T00:00:00Z"},
                    {"text": "Use B", "last_updated": "2026-05-03T00:00:30Z"},
                ],
            }
        ),
        encoding="utf-8",
    )

    review = _review_memory()(path)

    conflict_suggestion = (
        "Review possible memory conflict in: decisions. "
        "[trigger: conflict_detected; Accept / Dismiss / Snooze]"
    )
    assert "conflict_detected" in review.active_trigger_ids
    assert conflict_suggestion in review.suggestions


def test_memory_review_snoozes_missing_next_action_trigger(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {"text": "Prepare handoff"},
            }
        ),
        encoding="utf-8",
    )
    clear_snoozes = _clear_memory_review_trigger_snoozes()
    snooze = _snooze_memory_review_triggers()

    try:
        clear_snoozes()
        before = _review_memory()(path)
        snooze(["missing_next_action"])
        after = _review_memory()(path)
    finally:
        clear_snoozes()

    assert "missing_next_action" in before.active_trigger_ids
    assert any("[trigger: missing_next_action;" in item for item in before.suggestions)
    assert "missing_next_action" not in after.active_trigger_ids
    assert not any("[trigger: missing_next_action;" in item for item in after.suggestions)


def test_memory_review_logs_session_trigger_actions() -> None:
    clear_actions = _clear_memory_review_trigger_snoozes()
    snooze = _snooze_memory_review_triggers()
    dismiss = _dismiss_memory_review_triggers()
    get_actions = _get_memory_review_trigger_actions()

    try:
        clear_actions()
        snooze(["stale_intent"])
        dismiss(["missing_next_action"])
        actions = get_actions()
    finally:
        clear_actions()

    assert [(getattr(item, "action"), getattr(item, "trigger_id")) for item in actions] == [
        ("snooze", "stale_intent"),
        ("dismiss", "missing_next_action"),
    ]


def test_memory_review_clears_session_trigger_actions() -> None:
    clear_actions = _clear_memory_review_trigger_snoozes()
    snooze = _snooze_memory_review_triggers()
    get_actions = _get_memory_review_trigger_actions()

    clear_actions()
    snooze(["stale_intent"])
    clear_actions()

    assert get_actions() == []


def test_memory_review_surfaces_repeated_patch_decision_trigger(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {"text": "Review repeated patches"},
                "next_action": {"text": "Capture decision"},
                "relevant_files": [
                    {
                        "path": f"src/file_{index}.py",
                        "why": "patch_apply target",
                        "source": "observed",
                        "updated_by": "mcp patch_apply",
                    }
                    for index in range(3)
                ],
            }
        ),
        encoding="utf-8",
    )

    review = _review_memory()(path)

    suggestion = (
        'Capture a decision after repeated patches with: vib memory decide "...". '
        "[trigger: missing_decision_after_patches; Accept / Dismiss / Snooze]"
    )
    assert "missing_decision_after_patches" in review.active_trigger_ids
    assert suggestion in review.suggestions
