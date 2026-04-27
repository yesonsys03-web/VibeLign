import subprocess
from pathlib import Path

from vibelign.commands.transfer_git_context import (
    get_working_tree_summary,
    get_work_memory_staleness_warning,
    should_include_handoff_path,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def test_should_include_handoff_path_filters_generated_dirs() -> None:
    assert should_include_handoff_path("vibelign/core/work_memory.py")
    assert should_include_handoff_path(".gitignore")
    assert should_include_handoff_path(".github/workflows/ci.yml")
    assert not should_include_handoff_path(".git/config")
    assert not should_include_handoff_path("vibelign.egg-info/PKG-INFO")
    assert not should_include_handoff_path("src/__pycache__/app.pyc")


def test_work_memory_staleness_warning_when_watch_memory_precedes_commit(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init")
    (tmp_path / "tracked.py").write_text("ok\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.py")
    _git(tmp_path, "commit", "-m", "initial")
    work_memory = tmp_path / ".vibelign" / "work_memory.json"
    work_memory.parent.mkdir()
    work_memory.write_text(
        """
{
  "schema_version": 1,
  "updated_at": "2000-01-01T00:00:00Z",
  "recent_events": [
    {
      "time": "2000-01-01T00:00:00Z",
      "kind": "modified",
      "path": "tracked.py",
      "message": "old watch event"
    }
  ],
  "relevant_files": [],
  "warnings": [],
  "decisions": [],
  "verification": []
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    warning = get_work_memory_staleness_warning(tmp_path)

    assert warning is not None
    assert "work_memory/watch data may be stale" in warning


def test_working_tree_summary_counts_and_includes_untracked_files(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    for index in range(9):
        (tmp_path / f"tracked_{index}.py").write_text("before\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    for index in range(9):
        (tmp_path / f"tracked_{index}.py").write_text(
            "before\nafter\n", encoding="utf-8"
        )
    for index in range(3):
        (tmp_path / f"untracked_{index}.py").write_text("new\n", encoding="utf-8")

    summary = get_working_tree_summary(tmp_path, max_items=20)

    assert summary["count"] == 12
    assert summary["summary"] == "커밋되지 않은 변경 12개 파일"
    assert "untracked_2.py" in summary["files"]
    assert "untracked_2.py — untracked" in summary["details"]


def test_working_tree_summary_keeps_readable_unicode_paths(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    unicode_path = tmp_path / "규칙수정안.md"
    unicode_path.write_text("handoff note\n", encoding="utf-8")

    summary = get_working_tree_summary(tmp_path, max_items=20)

    assert "규칙수정안.md" in summary["files"]
    assert "규칙수정안.md — untracked" in summary["details"]
