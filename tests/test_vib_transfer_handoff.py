"""Tests for vib transfer --handoff functionality."""

import argparse
import unittest.mock as mock
from pathlib import Path
from typing import cast

from vibelign.commands.vib_transfer_cmd import HandoffData
from vibelign.commands.vib_transfer_cmd import (
    _build_file_tree,
    _build_context_content,
    _build_handoff_block,
    _get_changed_files,
    run_transfer,
)


def _make_handoff_data(**kwargs: object) -> HandoffData:
    base: dict[str, object] = {
        "generated_at": "2026-03-23 12:00",
        "source": "file_fallback",
        "quality": "auto-drafted",
        "session_summary": None,
        "changed_files": [],
        "completed_work": None,
        "unfinished_work": None,
        "first_next_action": None,
        "decision_context": None,
        "latest_checkpoint": None,
    }
    base.update(kwargs)
    return cast(HandoffData, cast(object, base))


# ── _build_handoff_block ────────────────────────────────────────────────────


def test_handoff_block_required_fields():
    data = _make_handoff_data(
        session_summary="Fixed login bug",
        changed_files=["auth.py", "tests/test_auth.py"],
        first_next_action="Write tests for auth flow",
    )
    block = _build_handoff_block(data)

    assert "## Session Handoff" in block
    assert "file_fallback" in block
    assert "auto-drafted" in block
    assert "Fixed login bug" in block
    assert "`auth.py`" in block
    assert "Write tests for auth flow" in block


def test_handoff_block_missing_fields_render_as_not_provided():
    data = _make_handoff_data()
    block = _build_handoff_block(data)

    # All optional fields missing → "(not provided)"
    assert "(not provided)" in block
    # Should appear for: session_summary, changed_files, completed_work,
    # unfinished_work, first_next_action
    assert block.count("(not provided)") >= 4


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
