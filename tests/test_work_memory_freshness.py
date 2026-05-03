import json
from pathlib import Path

from vibelign.core.memory.store import build_handoff_summary, load_memory_state


def test_migrated_verification_is_stale_when_scope_is_unknown(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "verification_updated_at": "2026-05-02T10:00:00Z",
                "verification": ["uv run pytest tests/test_transfer_git_context.py -> passed"],
            }
        ),
        encoding="utf-8",
    )

    state = load_memory_state(path)

    assert state.verification[0].stale is True
    assert state.verification[0].scope_unknown is True
    assert state.verification[0].last_updated == "2026-05-02T10:00:00Z"


def test_handoff_renders_stale_verification_label(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "verification": ["uv run pytest tests/test_transfer_git_context.py -> passed"],
            }
        ),
        encoding="utf-8",
    )

    summary = build_handoff_summary(path)

    assert summary is not None
    assert summary.get("verification") == [
        "uv run pytest tests/test_transfer_git_context.py -> passed (stale: scope unknown)"
    ]
    assert summary.get("verification_freshness") == "stale"


def test_handoff_does_not_duplicate_existing_stale_label(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "verification": [
                    "uv run pytest tests/test_transfer_git_context.py -> passed (stale: scope unknown) (stale: scope unknown)"
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = build_handoff_summary(path)

    assert summary is not None
    assert summary.get("verification") == [
        "uv run pytest tests/test_transfer_git_context.py -> passed (stale: scope unknown)"
    ]
