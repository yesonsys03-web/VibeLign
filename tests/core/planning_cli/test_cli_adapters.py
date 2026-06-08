from pathlib import Path
from unittest.mock import patch

from vibelign.core.planning_cli.cli_adapters import (
    PlanningCliResult,
    classify_cli_output,
    probe_cli_candidates,
    select_adapter,
)


def test_classifies_login_and_empty_output() -> None:
    assert classify_cli_output(1, "", "please login") == "not_logged_in"
    assert classify_cli_output(0, "", "") == "bad_output"


def test_successful_output_is_not_reclassified_by_broad_auth_words() -> None:
    output = "검토 결과: 로그인 화면과 authentication flow를 기획안에 추가하세요."

    assert classify_cli_output(0, output, "") == "ok"


def test_select_adapter_keeps_pr4_to_codex_only() -> None:
    assert select_adapter("auto") == "codex"
    assert select_adapter("codex") == "codex"


def test_probe_does_not_read_token_or_session_files(tmp_path: Path) -> None:
    with patch("vibelign.core.planning_cli.cli_adapters.shutil.which", return_value=None):
        candidates = probe_cli_candidates()

    assert [candidate.adapter for candidate in candidates] == ["codex", "claude", "agy", "opencode"]
    assert all(candidate.executable is None for candidate in candidates)
    assert not (tmp_path / ".claude").exists()


def test_planning_cli_result_status_values() -> None:
    result = PlanningCliResult(
        status="timeout",
        stdout="partial",
        stderr="",
        exit_code=None,
        duration_ms=1,
    )

    assert result.status == "timeout"
