"""Pin post-commit hook 가시성 — 자동 백업 실패 시 stderr + 통합 에러 로그 양쪽으로 알린다.

Why: 이전 버전은 except 블록에서 즉시 return 해 자동백업 ON 인 사용자가 백업이
만들어지지 않은 줄도 모른 채 데이터 부재를 인지 못 하는 UX 버그가 있었다.
프로젝트의 통합 로깅(`vibelign/core/error_log.py::record_cli_error`)은 이미
redaction + retention + 회전 + 동시 쓰기 락 을 갖추고 있으므로 그쪽에 위임한다.
git commit 흐름은 막지 않으면서도 가시성을 확보하는 게 의도된 동작.
"""
from __future__ import annotations

import io
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.internal_post_commit_cmd import run_internal_post_commit


def test_post_commit_failure_emits_stderr_and_routes_to_record_cli_error(tmp_path: Path) -> None:
    captured = io.StringIO()

    with patch(
        "vibelign.commands.internal_post_commit_cmd.create_post_commit_backup",
        side_effect=RuntimeError("RUST_ENGINE_UNAVAILABLE: rust engine binary missing"),
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_commit_message"
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_cli_error"
    ) as record_call, patch(
        "sys.stdin", io.StringIO("fix: trigger failure path\n")
    ), patch("sys.stderr", captured):
        run_internal_post_commit(Namespace(sha="abc1234"), root=tmp_path)

    stderr_output = captured.getvalue()
    assert "[vibelign] 자동 백업 실패" in stderr_output
    assert "RUST_ENGINE_UNAVAILABLE" in stderr_output

    record_call.assert_called_once()
    args, _ = record_call.call_args
    log_root, exc_info, argv = args
    assert log_root == tmp_path
    assert exc_info[0] is RuntimeError
    assert argv == ["_internal_post_commit", "abc1234"]


def test_post_commit_success_does_not_emit_visibility(tmp_path: Path) -> None:
    """성공 경로에서는 stderr 출력 없음 — record_cli_error 도 호출 안 함."""
    captured = io.StringIO()

    with patch(
        "vibelign.commands.internal_post_commit_cmd.create_post_commit_backup"
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_commit_message"
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_cli_error"
    ) as record_call, patch(
        "sys.stdin", io.StringIO("feat: ok\n")
    ), patch("sys.stderr", captured):
        run_internal_post_commit(Namespace(sha="def5678"), root=tmp_path)

    assert captured.getvalue() == ""
    record_call.assert_not_called()


def test_post_commit_failure_does_not_propagate(tmp_path: Path) -> None:
    """git commit 흐름을 깨면 안 되므로 어떤 예외도 함수 밖으로 새지 않는다.

    record_cli_error 가 자체 실패해도 (예: 로그 디렉토리 권한 등) stderr 출력은
    여전히 시도되고, run_internal_post_commit 자체는 정상 return 한다.
    """
    with patch(
        "vibelign.commands.internal_post_commit_cmd.create_post_commit_backup",
        side_effect=RuntimeError("any internal error"),
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_commit_message"
    ), patch(
        "vibelign.commands.internal_post_commit_cmd.record_cli_error",
        side_effect=OSError("log dir not writable"),
    ), patch(
        "sys.stdin", io.StringIO("msg\n")
    ), patch("sys.stderr", io.StringIO()):
        run_internal_post_commit(Namespace(sha="0000000"), root=tmp_path)
