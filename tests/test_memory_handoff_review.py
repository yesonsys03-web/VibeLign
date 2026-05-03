import json
from pathlib import Path

from vibelign.core.memory.handoff_review import build_handoff_review


def test_handoff_review_returns_stable_empty_shape_without_writes(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"

    review = build_handoff_review(path)

    assert review == {
        "read_only": False,
        "downgrade_warning": "",
        "active_intent": "",
        "next_action": "",
        "decisions": [],
        "relevant_files": [],
        "observed_context": [],
        "verification": [],
        "warnings": [],
        "redaction": {"secret_hits": 0, "privacy_hits": 0, "summarized_fields": 0},
    }
    assert not path.exists()


def test_handoff_review_uses_redacted_memory_summary(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    secret_text = "tok" + "en=fixtureSecretValue1234"
    _ = path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {"text": f"Fix {secret_text}", "source": "explicit"},
                "next_action": {"text": "Check /Users/alice/project", "source": "explicit"},
                "decisions": [{"text": "Keep handoff review compact", "source": "explicit"}],
                "relevant_files": [
                    {
                        "path": "vibelign/core/memory/hand_off_review.py",
                        "why": "handoff review API",
                        "source": "explicit",
                    },
                    {"path": "scratch.py", "why": "watch noise", "source": "observed"},
                ],
                "observed_context": [
                    {"kind": "modified", "summary": "review changed", "path": "scratch.py"}
                ],
                "verification": [{"command": "pytest tests/test_memory_handoff_review.py"}],
                "risks": [{"text": "Internal host build.local appeared", "source": "system"}],
            }
        ),
        encoding="utf-8",
    )

    review = build_handoff_review(path)
    rendered = json.dumps(review, sort_keys=True)

    assert review["read_only"] is False
    assert "fixtureSecretValue1234" not in rendered
    assert "/Users/alice" not in rendered
    assert "build.local" not in rendered
    assert review["active_intent"] == "Fix token=[redacted]"
    assert review["next_action"] == "Check [local-path]"
    assert review["decisions"] == ["Keep handoff review compact"]
    assert review["relevant_files"] == [
        "vibelign/core/memory/hand_off_review.py — handoff review API"
    ]
    assert review["observed_context"] == ["modified: scratch.py — review changed"]
    assert review["verification"] == ["pytest tests/test_memory_handoff_review.py"]
    assert review["warnings"] == ["Internal host [internal-host] appeared"]
    assert review["redaction"] == {"secret_hits": 2, "privacy_hits": 2, "summarized_fields": 0}


def test_handoff_review_marks_newer_schema_read_only(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    _ = path.write_text(
        json.dumps({"schema_version": 99, "active_intent": {"text": "Future goal"}}),
        encoding="utf-8",
    )

    review = build_handoff_review(path)

    assert review["read_only"] is True
    assert "schema_version=99" in str(review["downgrade_warning"])
    assert review["decisions"] == []
