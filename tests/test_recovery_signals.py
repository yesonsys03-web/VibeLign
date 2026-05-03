import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from vibelign.core.local_checkpoints import CheckpointSummary
from vibelign.core.recovery.signals import collect_basic_signals


def _git(root: Path, *args: str) -> None:
    _ = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_collect_basic_signals_includes_staged_paths(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test User")
    (root / "app.py").write_text("print('one')\n", encoding="utf-8")
    _git(root, "add", "app.py")
    _git(root, "commit", "-m", "initial")
    (root / "app.py").write_text("print('two')\n", encoding="utf-8")
    _git(root, "add", "app.py")

    signals = collect_basic_signals(root)

    assert signals.changed_paths == ["app.py"]


def test_collect_basic_signals_reads_work_memory_project_anchor_and_reports(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    meta = root / ".vibelign"
    reports = meta / "reports"
    reports.mkdir(parents=True)
    (meta / "work_memory.json").write_text(
        json.dumps(
            {
                "relevant_files": [
                    {"path": "src/ui.py", "why": "user set", "source": "explicit"},
                    {"path": "src/button.py", "why": "watch", "source": "watch"},
                ],
                "recent_events": [
                    {"kind": "edit", "path": "src/recent.py", "message": "changed"},
                    {"kind": "checkpoint", "path": "checkpoint", "message": "saved"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (meta / "project_map.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "project_name": "demo",
                "files": {
                    "src/ui.py": {"category": "ui", "anchors": ["UI_ANCHOR"]},
                    "src/button.py": {"category": "ui", "anchors": ["UI_ANCHOR"]},
                    "src/recent.py": {"category": "core", "anchors": ["RECENT_ANCHOR"]},
                },
            }
        ),
        encoding="utf-8",
    )
    (meta / "anchor_meta.json").write_text(
        json.dumps(
            {
                "UI_ANCHOR": {"intent": "Render UI"},
                "RECENT_ANCHOR": {"intent": "Recent edit"},
            }
        ),
        encoding="utf-8",
    )
    (reports / "guard_latest.json").write_text(
        json.dumps({"data": {"status": "fail", "blocked": True, "summary": "Guard failed"}}),
        encoding="utf-8",
    )
    (reports / "explain_latest.json").write_text(
        json.dumps({"data": {"summary": "Changed UI"}}),
        encoding="utf-8",
    )

    signals = collect_basic_signals(root)

    assert signals.explicit_relevant_paths == ["src/ui.py"]
    assert signals.recent_patch_paths == ["src/button.py", "src/recent.py"]
    assert signals.project_map_categories["src/ui.py"] == "ui"
    assert signals.anchor_intents_by_path["src/button.py"] == ["Render UI"]
    assert signals.guard_has_failures is True
    assert signals.guard_summary == "Guard failed"
    assert signals.explain_summary == "Changed UI"


def test_collect_basic_signals_requires_valid_checkpoint_preview(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    checkpoint = CheckpointSummary(
        checkpoint_id="20260502T000000000000Z_test",
        created_at="2026-05-02T00:00:00Z",
        message="before work",
        file_count=3,
    )

    with patch("vibelign.core.recovery.signals.list_checkpoints", return_value=[checkpoint]), patch(
        "vibelign.core.recovery.signals.has_changes_since_checkpoint", return_value=True
    ), patch(
        "vibelign.core.recovery.signals.preview_restore", return_value={"ok": True, "files": []}
    ):
        signals = collect_basic_signals(root)

    assert signals.safe_checkpoint_candidate is not None
    assert signals.safe_checkpoint_candidate.metadata_complete is True
    assert signals.safe_checkpoint_candidate.preview_available is True
    assert signals.safe_checkpoint_candidate.predates_change is True


def test_collect_basic_signals_rejects_checkpoint_without_preview(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    checkpoint = CheckpointSummary(
        checkpoint_id="20260502T000000000000Z_test",
        created_at="2026-05-02T00:00:00Z",
        message="before work",
        file_count=3,
    )

    with patch("vibelign.core.recovery.signals.list_checkpoints", return_value=[checkpoint]), patch(
        "vibelign.core.recovery.signals.has_changes_since_checkpoint", return_value=True
    ), patch("vibelign.core.recovery.signals.preview_restore", return_value={}):
        signals = collect_basic_signals(root)

    assert signals.safe_checkpoint_candidate is None
