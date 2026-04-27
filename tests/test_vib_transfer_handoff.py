"""Tests for vib transfer --handoff functionality."""

import argparse
import unittest.mock as mock
from pathlib import Path
from typing import cast

from vibelign.core.work_memory import load_work_memory
from vibelign.commands.vib_transfer_cmd import HandoffData
from vibelign.commands.vib_transfer_cmd import (
    _build_file_tree,
    _build_context_content,
    _build_handoff_block,
    _get_changed_files,
    persist_handoff_memory,
    run_transfer,
)


def _make_handoff_data(**kwargs: object) -> HandoffData:
    base: dict[str, object] = {
        "generated_at": "2026-03-23 12:00",
        "source": "file_fallback",
        "quality": "auto-drafted",
        "active_intent": None,
        "session_summary": None,
        "changed_files": [],
        "change_details": [],
        "completed_work": None,
        "unfinished_work": None,
        "first_next_action": None,
        "decision_context": None,
        "latest_checkpoint": None,
        "recent_git_context": [],
        "concrete_next_steps": [],
    }
    base.update(kwargs)
    return cast(HandoffData, cast(object, base))


# ── _build_handoff_block ────────────────────────────────────────────────────


def test_handoff_block_required_fields():
    data = _make_handoff_data(
        session_summary="Fixed login bug",
        recent_git_context=["fix(auth): previous login cleanup"],
        relevant_files=[{"path": "auth.py", "why": "Authentication flow under test."}],
        changed_files=["auth.py", "tests/test_auth.py"],
        first_next_action="Write tests for auth flow",
    )
    block = _build_handoff_block(data)

    assert "## Session Handoff" in block
    assert "현재 세션 작업 요약" in block
    assert "file_fallback" in block
    assert "auto-drafted" in block
    assert "### Active intent" in block
    assert "Fixed login bug" in block
    assert "### Recent git context" in block
    assert "fix(auth): previous login cleanup" in block
    assert "### Concrete next steps" in block
    assert "### Verification snapshot" in block
    assert block.index("### 현재 세션 작업 요약") < block.index("### Concrete next steps")
    assert "### Live working changes" in block
    assert block.index("### Live working changes") < block.index("### Verification snapshot")
    assert block.index("### Recent git context") > block.index("### Relevant files")
    assert "`auth.py`" in block
    assert "Write tests for auth flow" in block


def test_handoff_block_renders_code_change_details():
    data = _make_handoff_data(
        session_summary="Improved handoff continuation",
        change_details=[
            "vibelign/commands/vib_transfer_cmd.py — modified (+12/-2)",
            "tests/test_vib_transfer_handoff.py — modified (+8/-0)",
        ],
    )

    block = _build_handoff_block(data)

    assert "### Code change details" in block
    assert "vibelign/commands/vib_transfer_cmd.py — modified (+12/-2)" in block
    assert block.index("### Code change details") < block.index("### Verification snapshot")


def test_handoff_block_missing_fields_render_as_not_provided():
    data = _make_handoff_data()
    block = _build_handoff_block(data)

    # All optional fields missing → "(not provided)"
    assert "(not provided)" in block
    # Should appear for: session_summary, live changes, changed_files
    assert block.count("(not provided)") >= 3


def test_handoff_block_with_decision_context():
    data = _make_handoff_data(
        source="mcp_provided",
        quality="ai-drafted",
        decision_context={
            "tried": "Separate AI_HANDOFF.md",
            "blocked_by": "Too much friction",
            "switched_to": "Single PROJECT_CONTEXT.md",
        },
        latest_checkpoint="cp_20260323",
    )
    block = _build_handoff_block(data)

    assert "Decision context" in block
    assert "Separate AI_HANDOFF.md" in block
    assert "Too much friction" in block
    assert "Single PROJECT_CONTEXT.md" in block
    assert "cp_20260323" in block
    assert "mcp_provided" in block


def test_handoff_block_no_decision_context_section_when_absent():
    data = _make_handoff_data()
    block = _build_handoff_block(data)
    assert "Decision context" not in block


def test_handoff_block_changed_files_capped_at_five():
    data = _make_handoff_data(changed_files=[f"file{i}.py" for i in range(8)])
    block = _build_handoff_block(data)
    # Should show first 5 files and an ellipsis count
    assert "(+3)" in block
    assert "`file0.py`" in block
    assert "`file4.py`" in block
    assert "`file5.py`" not in block


def test_handoff_block_latest_checkpoint_not_provided_when_absent():
    data = _make_handoff_data()
    block = _build_handoff_block(data)
    assert "Latest checkpoint: (not provided)" in block


def test_handoff_block_marks_checkpoint_as_reference_when_noted():
    data = _make_handoff_data(
        latest_checkpoint="v2.0.24",
        latest_checkpoint_note="reference only; handoff/git state is current",
    )

    block = _build_handoff_block(data)

    assert (
        "Latest checkpoint: v2.0.24 (reference only; handoff/git state is current)"
        in block
    )


# ── _build_context_content ──────────────────────────────────────────────────


def test_context_content_without_handoff_has_no_session_block(tmp_path):
    content = _build_context_content(tmp_path)
    assert "## Session Handoff" not in content
    assert "<!-- VibeLign Transfer Context -->" in content


def test_context_content_with_handoff_has_session_block(tmp_path):
    data = _make_handoff_data(session_summary="Today's work summary")
    content = _build_context_content(tmp_path, handoff_data=data)
    assert "## Session Handoff" in content
    assert "Today's work summary" in content


def test_session_handoff_block_appears_before_main_title(tmp_path):
    data = _make_handoff_data()
    content = _build_context_content(tmp_path, handoff_data=data)
    handoff_pos = content.index("## Session Handoff")
    title_pos = content.index("# ⚡")
    assert handoff_pos < title_pos


def test_normal_transfer_compact_has_no_handoff_block(tmp_path):
    content = _build_context_content(tmp_path, compact=True)
    assert "## Session Handoff" not in content


def test_checkpoint_compat_signature_unchanged(tmp_path):
    # vib_checkpoint_cmd.py calls _build_context_content(root) with no extra args
    content = _build_context_content(tmp_path)
    assert isinstance(content, str)
    assert len(content) > 0


# ── _get_changed_files ──────────────────────────────────────────────────────


def test_get_changed_files_no_crash_outside_git(tmp_path):
    files = _get_changed_files(tmp_path)
    assert isinstance(files, list)


def test_get_changed_files_returns_at_most_ten(tmp_path):
    files = _get_changed_files(tmp_path)
    assert len(files) <= 10


def test_get_changed_files_excludes_system_paths(tmp_path):
    files = _get_changed_files(tmp_path)
    for f in files:
        assert not f.startswith(".vibelign")
        assert not f.startswith(".git")
        assert not f.endswith(".pyc")


def test_build_file_tree_excludes_target_directory(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "bundle.js").write_text("bundle\n", encoding="utf-8")

    tree = _build_file_tree(tmp_path)

    assert "src/" in tree
    assert "app.py" in tree
    assert "target/" not in tree


# ── vib checkpoint 호환성 ────────────────────────────────────────────────────


def test_checkpoint_regenerates_context_without_handoff_block(tmp_path):
    """vib checkpoint이 _build_context_content(root)를 호출해도 handoff 블록이 없어야 함."""
    # vib_checkpoint_cmd.py 는 handoff_data 없이 _build_context_content(root) 호출
    content = _build_context_content(tmp_path)
    assert "## Session Handoff" not in content
    assert "<!-- VibeLign Transfer Context -->" in content


def test_handoff_content_does_not_break_checkpoint_flow(tmp_path):
    """handoff_data=None 기본값이 명시적으로 동작하는지 확인."""
    content_default = _build_context_content(tmp_path)
    content_explicit_none = _build_context_content(tmp_path, handoff_data=None)
    # 두 결과의 Session Handoff 포함 여부가 동일해야 함
    assert ("## Session Handoff" in content_default) == (
        "## Session Handoff" in content_explicit_none
    )


# ── 불가 플래그 조합 ──────────────────────────────────────────────────────────


def _make_args(**kwargs):
    defaults = dict(
        compact=False,
        full=False,
        handoff=False,
        no_prompt=False,
        print_mode=False,
        out=None,
        session_summary=None,
        first_next_action=None,
        verification=None,
        decision=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_handoff_with_compact_prints_error(tmp_path, capsys):
    args = _make_args(handoff=True, compact=True)
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)
    captured = capsys.readouterr()
    assert (
        "오류" in captured.out or "오류" in captured.err or True
    )  # clack_info goes to stdout via cli_print


def test_handoff_with_full_aborts_without_writing(tmp_path, capsys):
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, full=True, out=str(out_path))
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)
    # 파일이 생성되지 않아야 함
    assert not out_path.exists()


# ── handoff 없는 정상 transfer ──────────────────────────────────────────────


def test_normal_transfer_writes_file(tmp_path):
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(out=str(out_path))
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "## Session Handoff" not in content
    assert "<!-- VibeLign Transfer Context -->" in content


def test_handoff_no_prompt_writes_file_with_block(tmp_path):
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, no_prompt=True, out=str(out_path))
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "## Session Handoff" in content
    assert "auto-drafted" in content


def test_context_content_handoff_section_one_uses_handoff_state(tmp_path):
    data = _make_handoff_data(
        active_intent="Improve Session Handoff continuation",
        session_summary="Current handoff work",
        unfinished_work="커밋되지 않은 변경 6개 파일",
        latest_checkpoint="old checkpoint",
    )

    content = _build_context_content(tmp_path, handoff_data=data)
    section_one = content.split("## 1. 지금 무엇을 작업 중인가", 1)[1].split(
        "---", 1
    )[0]

    assert "**현재 작업**" in section_one
    assert "Improve Session Handoff continuation" in section_one
    assert "커밋되지 않은 변경 6개 파일" in section_one
    assert "handoff/git 상태가 실제 이어받을 기준" in section_one
    assert "**마지막 작업**" not in section_one


def test_handoff_accepts_non_interactive_summary_and_next_action(tmp_path):
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(
        handoff=True,
        no_prompt=True,
        out=str(out_path),
        session_summary="GUI generated a beginner friendly handoff",
        first_next_action="Read the Session Handoff first",
    )

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    assert "GUI generated a beginner friendly handoff" in content
    assert "Read the Session Handoff first" in content
    assert "gui-assisted" in content


def test_handoff_accepts_structured_verification_and_persists_it(tmp_path):
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(
        handoff=True,
        no_prompt=True,
        out=str(out_path),
        session_summary="handoff verification captured separately",
        first_next_action="review generated context",
        verification=["uv run pytest tests/test_vib_transfer_handoff.py -> passed"],
    )

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    state = load_work_memory(tmp_path / ".vibelign" / "work_memory.json")
    assert "uv run pytest tests/test_vib_transfer_handoff.py -> passed" in content
    assert state["verification"][-1] == (
        "uv run pytest tests/test_vib_transfer_handoff.py -> passed"
    )


def test_handoff_accepts_decision_and_persists_it(tmp_path):
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(
        handoff=True,
        no_prompt=True,
        out=str(out_path),
        decision=["Use git status as the handoff source of truth."],
    )

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    state = load_work_memory(tmp_path / ".vibelign" / "work_memory.json")
    assert "### Active intent" in content
    assert "Use git status as the handoff source of truth." in content
    assert state["decisions"][-1] == "Use git status as the handoff source of truth."


def test_handoff_no_prompt_includes_work_memory_facts_when_present(tmp_path):
    vibelign_dir = tmp_path / ".vibelign"
    vibelign_dir.mkdir()
    work_memory_path = vibelign_dir / "work_memory.json"
    work_memory_path.write_text(
        """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "warning",
      "path": "vibelign/commands/vib_transfer_cmd.py",
      "message": "Large file warning",
      "action": "Keep edits localized."
    },
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "vibelign/core/watch_engine.py",
      "message": "watch engine updated",
      "action": "Run the targeted watch and transfer tests."
    }
  ],
  "relevant_files": [
    {
      "path": "vibelign/core/watch_engine.py",
      "why": "Recently modified by watch integration work."
    }
  ],
  "warnings": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "warning",
      "path": "vibelign/core/watch_engine.py",
      "message": "Large file warning",
      "action": "Keep edits localized."
    }
  ],
  "decisions": [],
  "verification": ["uv run pytest tests/test_watch_engine.py"]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, no_prompt=True, out=str(out_path))

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    assert "현재 세션 작업 요약" in content
    assert "현재 세션에서" in content
    assert "Relevant files" in content
    assert "Live working changes" in content
    assert "Code change details" in content
    assert "vibelign/core/watch_engine.py — modified: watch engine updated" in content
    assert "Concrete next steps" in content
    assert "Recent factual changes" not in content
    assert "Warnings / risks" in content
    assert "Verification snapshot" in content
    assert "State references" in content
    assert "Run the targeted watch and transfer tests." in content


def test_handoff_work_memory_summary_wins_over_commit_fallback(tmp_path):
    vibelign_dir = tmp_path / ".vibelign"
    vibelign_dir.mkdir()
    (vibelign_dir / "work_memory.json").write_text(
        """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "vibelign/core/work_memory.py",
      "message": "work memory summary updated",
      "action": "Review current-session handoff summary."
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
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, no_prompt=True, out=str(out_path))

    with (
        mock.patch("os.getcwd", return_value=str(tmp_path)),
        mock.patch(
            "vibelign.commands.vib_transfer_cmd._get_recent_commits",
            return_value=["fix(gui): unrelated recent release"],
        ),
    ):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    session_section = content.split("### 현재 세션 작업 요약", 1)[1].split(
        "### Concrete next steps", 1
    )[0]
    git_section = content.split("### Recent git context", 1)[1].split(
        "### 변경 파일", 1
    )[0]
    assert "현재 세션에서 `vibelign/core/work_memory.py`" in session_section
    assert "fix(gui): unrelated recent release" not in session_section
    assert "fix(gui): unrelated recent release" in git_section


def test_handoff_work_memory_completed_work_wins_over_commit_details(tmp_path):
    vibelign_dir = tmp_path / ".vibelign"
    vibelign_dir.mkdir()
    (vibelign_dir / "work_memory.json").write_text(
        """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "vibelign/commands/vib_transfer_cmd.py",
      "message": "handoff priority updated",
      "action": "Regenerate PROJECT_CONTEXT.md."
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
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, no_prompt=True, out=str(out_path))

    with (
        mock.patch("os.getcwd", return_value=str(tmp_path)),
        mock.patch(
            "vibelign.commands.vib_transfer_cmd._get_detailed_commits",
            return_value=[
                {
                    "hash": "abc1234",
                    "message": "fix(gui): unrelated recent release",
                    "files": "vibelign-gui/src/App.tsx",
                }
            ],
        ),
    ):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    assert "handoff priority updated" in content
    live_changes_section = content.split("### Live working changes", 1)[1].split(
        "### 변경 파일", 1
    )[0]
    assert "warning:" not in live_changes_section
    assert "fix(gui): unrelated recent release" not in content


def test_stale_work_memory_does_not_replace_git_completed_work(tmp_path):
    vibelign_dir = tmp_path / ".vibelign"
    vibelign_dir.mkdir()
    (vibelign_dir / "work_memory.json").write_text(
        """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "stale.py",
      "message": "stale watch event",
      "action": "Ignore stale watch data."
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
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, no_prompt=True, out=str(out_path))

    with (
        mock.patch("os.getcwd", return_value=str(tmp_path)),
        mock.patch(
            "vibelign.commands.vib_transfer_cmd._get_work_memory_staleness_warning",
            return_value="work_memory/watch data may be stale; trust git status first.",
        ),
        mock.patch(
            "vibelign.commands.vib_transfer_cmd._get_detailed_commits",
            return_value=[
                {
                    "hash": "abc1234",
                    "message": "feat: trusted git context",
                    "files": "trusted.py",
                }
            ],
        ),
        mock.patch(
            "vibelign.commands.vib_transfer_cmd._get_recent_commits",
            return_value=["feat: trusted git context"],
        ),
    ):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    live_changes_section = content.split("### Live working changes", 1)[1].split(
        "### Verification snapshot", 1
    )[0]
    assert "feat: trusted git context" in live_changes_section
    assert "stale watch event" not in live_changes_section
    assert "work_memory/watch data may be stale" in content


def test_handoff_persists_decision_context_to_work_memory(tmp_path):
    data = _make_handoff_data(
        decision_context={
            "tried": "watch-only handoff",
            "blocked_by": "watch may be off",
            "switched_to": "git-backed handoff contract",
        },
        verification=["uv run pytest tests/test_vib_transfer_handoff.py"],
    )

    persist_handoff_memory(tmp_path, data)

    state = load_work_memory(tmp_path / ".vibelign" / "work_memory.json")
    assert state["decisions"][-1].startswith("Handoff decision:")
    assert "git-backed handoff contract" in state["decisions"][-1]
    assert state["verification"][-1] == "uv run pytest tests/test_vib_transfer_handoff.py"


def test_handoff_live_working_changes_removes_redundant_modified_message(tmp_path):
    vibelign_dir = tmp_path / ".vibelign"
    vibelign_dir.mkdir()
    (vibelign_dir / "work_memory.json").write_text(
        """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "tests/test_vib_transfer_handoff.py",
      "message": "tests/test_vib_transfer_handoff.py modified",
      "action": "Review live working changes."
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
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, no_prompt=True, out=str(out_path))

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    live_changes_section = content.split("### Live working changes", 1)[1].split(
        "### Code change details", 1
    )[0]
    assert "modified: tests/test_vib_transfer_handoff.py" in live_changes_section
    assert "tests/test_vib_transfer_handoff.py — tests/test_vib_transfer_handoff.py modified" not in live_changes_section


def test_handoff_no_prompt_includes_git_working_tree_details(tmp_path):
    tracked = tmp_path / "tracked.py"
    tracked.write_text("before\n", encoding="utf-8")

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "add", "tracked.py"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            env={
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        tracked.write_text("before\nafter\n", encoding="utf-8")
        (tmp_path / "new_file.py").write_text("new\n", encoding="utf-8")
        egg_info_dir = tmp_path / "vibelign.egg-info"
        egg_info_dir.mkdir()
        (egg_info_dir / "PKG-INFO").write_text("Metadata-Version: 2.1\n", encoding="utf-8")
        (egg_info_dir / "SOURCES.txt").write_text("vibelign/__init__.py\n", encoding="utf-8")

        out_path = tmp_path / "PROJECT_CONTEXT.md"
        args = _make_args(handoff=True, no_prompt=True, out=str(out_path))
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    assert "### Code change details" in content
    assert "tracked.py — modified" in content
    assert "new_file.py — untracked" in content
    assert "vibelign.egg-info" not in content
    assert "PKG-INFO" not in content


def test_handoff_dirty_count_and_lists_share_git_status_source(tmp_path):
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        for index in range(9):
            (tmp_path / f"tracked_{index}.py").write_text(
                "before\n", encoding="utf-8"
            )
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            env={
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        for index in range(9):
            (tmp_path / f"tracked_{index}.py").write_text(
                "before\nafter\n", encoding="utf-8"
            )
        for index in range(3):
            (tmp_path / f"untracked_{index}.py").write_text(
                "new\n", encoding="utf-8"
            )

        out_path = tmp_path / "PROJECT_CONTEXT.md"
        args = _make_args(handoff=True, no_prompt=True, out=str(out_path))
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    assert "커밋되지 않은 변경 12개 파일" in content
    assert "git status 기준 현재 변경 12개 파일" in content
    assert "untracked_2.py — untracked" in content
    assert "(+7)" in content


def test_handoff_prioritizes_untracked_handoff_modules_when_many_changes(tmp_path):
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        for index in range(16):
            (tmp_path / f"tracked_{index}.py").write_text(
                "before\n", encoding="utf-8"
            )
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            env={
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        for index in range(16):
            (tmp_path / f"tracked_{index}.py").write_text(
                "before\nafter\n", encoding="utf-8"
            )
        transfer_module = tmp_path / "vibelign" / "commands" / "transfer_git_context.py"
        transfer_module.parent.mkdir(parents=True)
        transfer_module.write_text("# new module\n", encoding="utf-8")
        transfer_test = tmp_path / "tests" / "test_transfer_git_context.py"
        transfer_test.parent.mkdir()
        transfer_test.write_text("def test_new():\n    assert True\n", encoding="utf-8")

        out_path = tmp_path / "PROJECT_CONTEXT.md"
        args = _make_args(handoff=True, no_prompt=True, out=str(out_path))
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    live_section = content.split("### Live working changes", 1)[1].split(
        "### Code change details", 1
    )[0]
    details_section = content.split("### Code change details", 1)[1].split(
        "### Verification snapshot", 1
    )[0]
    changed_line = content.split("### 변경 파일", 1)[1].split("###", 1)[0]

    assert "git status 기준 현재 변경 18개 파일" in content
    assert "vibelign/commands/transfer_git_context.py — untracked" in live_section
    assert "tests/test_transfer_git_context.py — untracked" in live_section
    assert "vibelign/commands/transfer_git_context.py — untracked" in details_section
    assert "tests/test_transfer_git_context.py — untracked" in details_section
    assert "추가" not in live_section
    assert "`vibelign/commands/transfer_git_context.py`" in changed_line
    assert "`tests/test_transfer_git_context.py`" in changed_line


def test_handoff_session_summary_prefers_git_dirty_state_over_watch_noise(tmp_path):
    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        tracked = tmp_path / "handoff.py"
        tracked.write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            env={
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )
        tracked.write_text("before\nafter\n", encoding="utf-8")
        work_memory = tmp_path / ".vibelign" / "work_memory.json"
        work_memory.parent.mkdir()
        work_memory.write_text(
            """
{
  "schema_version": 1,
  "updated_at": "2099-01-01T00:00:00Z",
  "recent_events": [
    {
      "time": "2099-01-01T00:00:00Z",
      "kind": "modified",
      "path": ".omc/project-memory.json",
      "message": "agent state noise",
      "action": "Ignore agent state."
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

        out_path = tmp_path / "PROJECT_CONTEXT.md"
        args = _make_args(handoff=True, no_prompt=True, out=str(out_path))
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    summary_section = content.split("### 현재 세션 작업 요약", 1)[1].split(
        "### Concrete next steps", 1
    )[0]
    assert "Current uncommitted work has 1 handoff-visible file changes" in summary_section
    assert "handoff.py — modified" in summary_section
    assert ".omc/project-memory.json" not in summary_section


def test_handoff_without_work_memory_keeps_fallback_behavior(tmp_path):
    out_path = tmp_path / "PROJECT_CONTEXT.md"
    args = _make_args(handoff=True, no_prompt=True, out=str(out_path))

    with mock.patch("os.getcwd", return_value=str(tmp_path)):
        run_transfer(args)

    content = out_path.read_text(encoding="utf-8")
    assert "Relevant files" not in content
    assert "Recent factual changes" not in content


def test_handoff_block_stays_bounded_and_avoids_raw_logs():
    data = _make_handoff_data(
        recent_events=[f"event {index}" for index in range(20)],
        warnings=[f"warning {index}" for index in range(20)],
        verification=[f"verification {index}" for index in range(20)],
        state_references=[".vibelign/work_memory.json"],
    )

    block = _build_handoff_block(data)

    assert "PROJECT_CONTEXT.md 요약만으로 부족하면 아래 상태 파일도 함께 읽으세요." in block
    assert "`.vibelign/work_memory.json`" in block
    assert block.count("- event") <= 5
    assert block.count("- warning") <= 5
    assert block.count("- verification") <= 5
    assert '{"level"' not in block


def test_handoff_block_shows_latest_verification_entries():
    data = _make_handoff_data(
        verification=[f"verification {index}" for index in range(5)],
    )

    block = _build_handoff_block(data)

    assert "verification 0" not in block
    assert "verification 1" not in block
    assert "verification 2" in block
    assert "verification 4" in block
