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


def _review_memory() -> Callable[[Path], _MemoryReviewLike]:
    module = import_module("vibelign.core.memory.review")
    return cast(Callable[[Path], _MemoryReviewLike], getattr(module, "review_memory"))


def test_memory_review_empty_memory_suggests_decision(tmp_path: Path) -> None:
    review = _review_memory()(tmp_path / ".vibelign" / "work_memory.json")

    assert review.has_memory is False
    assert review.suggestions == ['Add a decision with: vib memory decide "..."']


def test_memory_review_surfaces_next_action_and_stale_verification(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
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
    assert review.suggestions == [
        "Rerun stale verification: uv run python -m pytest tests/test_memory_review.py"
    ]


def test_memory_review_surfaces_downgrade_warning(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
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
    path.write_text(
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

    assert review.has_memory is True
    assert review.suggestions == [
        'Confirm the current goal with: vib memory decide "..."',
        "Capture the next handoff action with --first-next-action.",
        "Review warnings before using this memory as handoff truth.",
    ]


def test_memory_review_redacts_sensitive_text(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    secret_text = "tok" + "en=fixtureSecretValue1234"
    path.write_text(
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
    path.write_text(
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

    assert "Review stale intent or next action before handoff." in review.suggestions
    assert "Review stale relevant files before handoff." in review.suggestions
