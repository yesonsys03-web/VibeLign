import json
from argparse import Namespace
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_memory_cmd import (
    run_vib_memory_decide,
    run_vib_memory_intent,
    run_vib_memory_relevant,
    run_vib_memory_review,
    run_vib_memory_show,
)
from vibelign.core.memory.store import load_memory_state, set_memory_next_action


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".vibelign").mkdir(parents=True)
    return root


def test_memory_decide_saves_explicit_decision(tmp_path: Path) -> None:
    root = _project(tmp_path)

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_decide(Namespace(decision=["Use", "memory", "core"]))

    state = load_memory_state(root / ".vibelign" / "work_memory.json")
    assert [item.text for item in state.decisions] == ["Use memory core"]
    assert state.active_intent is not None
    assert state.active_intent.text == "Use memory core"
    assert state.active_intent.proposed is True


def test_memory_intent_confirms_active_intent(tmp_path: Path) -> None:
    root = _project(tmp_path)

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_decide(Namespace(decision=["Proposed", "goal"]))
        run_vib_memory_intent(Namespace(intent=["Confirmed", "goal"]))

    state = load_memory_state(root / ".vibelign" / "work_memory.json")
    assert state.active_intent is not None
    assert state.active_intent.text == "Confirmed goal"
    assert state.active_intent.proposed is False
    assert [item.text for item in state.decisions] == ["Proposed goal"]


def test_memory_relevant_saves_explicit_relevant_file(tmp_path: Path) -> None:
    root = _project(tmp_path)

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_relevant(Namespace(path="src/app.py", why=["main", "entry"]))

    state = load_memory_state(root / ".vibelign" / "work_memory.json")
    assert [(item.path, item.why, item.source) for item in state.relevant_files] == [
        ("src/app.py", "main entry", "explicit")
    ]


def test_memory_relevant_preserves_typed_decision(tmp_path: Path) -> None:
    root = _project(tmp_path)

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_decide(Namespace(decision=["Keep", "typed", "decision"]))
        run_vib_memory_relevant(Namespace(path="src/app.py", why=["main", "entry"]))

    state = load_memory_state(root / ".vibelign" / "work_memory.json")
    assert [item.text for item in state.decisions] == ["Keep typed decision"]
    assert state.active_intent is not None
    assert state.active_intent.text == "Keep typed decision"
    assert [(item.path, item.why, item.source) for item in state.relevant_files] == [
        ("src/app.py", "main entry", "explicit")
    ]


def test_memory_show_prints_current_state(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_decide(Namespace(decision=["Improve", "handoff"]))
        set_memory_next_action(root / ".vibelign" / "work_memory.json", "Rerun handoff tests")
        run_vib_memory_show(Namespace())

    output = capsys.readouterr().out
    assert "VibeLign Memory" in output
    assert "Improve handoff" in output
    assert "Next action: Rerun handoff tests" in output


def test_memory_review_prints_next_action(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    set_memory_next_action(root / ".vibelign" / "work_memory.json", "Review persisted next action")

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_review(Namespace())

    output = capsys.readouterr().out
    assert "VibeLign Memory Review" in output
    assert "Next action: Review persisted next action" in output
    assert "Decisions:" in output
    assert "Explicit relevant files:" in output
    assert "Observed context:" in output
    assert "Redaction: secrets=0, privacy=0, summarized=0" in output
    assert "Suggestions:" in output


def test_memory_review_audits_shown_triggers(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    memory_path = root / ".vibelign" / "work_memory.json"
    _ = memory_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_intent": {"text": "Prepare handoff"},
            }
        ),
        encoding="utf-8",
    )

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_review(Namespace())

    output = capsys.readouterr().out
    audit_path = root / ".vibelign" / "memory_audit.jsonl"
    payload = cast(
        dict[str, object],
        json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0]),
    )
    assert "VibeLign Memory Review" in output
    assert "Capture the next handoff action" in output
    assert payload["event"] == "memory_review_trigger_shown"
    assert payload["trigger"] == {
        "id": "missing_next_action",
        "action": "shown",
        "source": "vibmemoryreview",
    }
    assert memory_path.exists()


def test_memory_review_is_read_only_for_empty_memory(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_review(Namespace())

    output = capsys.readouterr().out
    assert "VibeLign Memory Review" in output
    assert "No memory yet" in output
    assert "Add a decision with: vib memory decide" in output
    assert not (root / ".vibelign" / "work_memory.json").exists()
    assert not (root / ".vibelign" / "memory_audit.jsonl").exists()


def test_memory_write_commands_refuse_newer_schema(tmp_path: Path) -> None:
    root = _project(tmp_path)
    memory_path = root / ".vibelign" / "work_memory.json"
    original = '{"schema_version": 99, "future_field": true}\n'
    _ = memory_path.write_text(original, encoding="utf-8")

    with patch("pathlib.Path.cwd", return_value=root):
        run_vib_memory_decide(Namespace(decision=["Do", "not", "write"]))
        run_vib_memory_intent(Namespace(intent=["Do", "not", "write"]))
        run_vib_memory_relevant(Namespace(path="src/app.py", why=["do", "not", "write"]))

    assert memory_path.read_text(encoding="utf-8") == original
