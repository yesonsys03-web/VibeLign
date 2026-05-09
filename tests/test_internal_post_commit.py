"""Pin post-commit hook 가시성 — 자동 백업 실패 시 stderr + 로그 파일 양쪽으로 알린다.

Why: 이전 버전은 except 블록에서 즉시 return 해 자동백업 ON 인 사용자가 백업이
만들어지지 않은 줄도 모른 채 데이터 부재를 인지 못 하는 UX 버그가 있었다.
가시성을 git commit 의 흐름을 막지 않으면서도 확보하는 게 의도된 동작.
"""
from __future__ import annotations

import io
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.internal_post_commit_cmd import (
    _POST_COMMIT_LOG_REL,
    run_internal_post_commit,
)


def test_post_commit_failure_writes_stderr_and_log(tmp_path: Path) -> None:
    captured = io.StringIO()

    with patch(
        "vibelign.commands.internal_post_commit_cmd.create_post_commit_backup",
        side_effect=RuntimeError("RUST_ENGINE_UNAVAILABLE: rust engine binary missing"),
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_commit_message"
    ), patch(
        "sys.stdin", io.StringIO("fix: trigger failure path\n")
    ), patch("sys.stderr", captured):
        run_internal_post_commit(Namespace(sha="abc1234"), root=tmp_path)

    stderr_output = captured.getvalue()
    assert "[vibelign] 자동 백업 실패" in stderr_output
    assert "RUST_ENGINE_UNAVAILABLE" in stderr_output

    log_path = tmp_path / _POST_COMMIT_LOG_REL
    assert log_path.exists(), "post-commit error log must be written"
    log_text = log_path.read_text(encoding="utf-8")
    assert "sha=abc1234" in log_text
    assert "RUST_ENGINE_UNAVAILABLE" in log_text
    assert "RuntimeError" in log_text


def test_post_commit_success_does_not_emit_visibility(tmp_path: Path) -> None:
    """성공 경로에서는 stderr 출력 없음 — log 파일도 만들지 않는다."""
    captured = io.StringIO()

    with patch(
        "vibelign.commands.internal_post_commit_cmd.create_post_commit_backup"
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_commit_message"
    ), patch(
        "sys.stdin", io.StringIO("feat: ok\n")
    ), patch("sys.stderr", captured):
        run_internal_post_commit(Namespace(sha="def5678"), root=tmp_path)

    assert captured.getvalue() == ""
    assert not (tmp_path / _POST_COMMIT_LOG_REL).exists()


def test_post_commit_failure_does_not_propagate(tmp_path: Path) -> None:
    """git commit 흐름을 깨면 안 되므로 어떤 예외도 함수 밖으로 새지 않는다."""
    with patch(
        "vibelign.commands.internal_post_commit_cmd.create_post_commit_backup",
        side_effect=RuntimeError("any internal error"),
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_commit_message"
    ), patch(
        "sys.stdin", io.StringIO("msg\n")
    ), patch("sys.stderr", io.StringIO()):
        run_internal_post_commit(Namespace(sha="0000000"), root=tmp_path)
