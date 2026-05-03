from pathlib import Path

from vibelign.core.memory.store import build_handoff_summary


def test_handoff_summary_for_missing_memory_has_stable_read_only_shape(tmp_path: Path) -> None:
    path = tmp_path / ".vibelign" / "work_memory.json"

    summary = build_handoff_summary(path)

    assert summary is not None
    assert summary == {"state_references": [".vibelign/work_memory.json"]}
    assert not path.exists()
