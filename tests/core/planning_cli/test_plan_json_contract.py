import json
from argparse import Namespace
from pathlib import Path

import pytest

from vibelign.commands.vib_plan_cmd import run_vib_plan
from vibelign.core.planning_cli.cli_adapters import PlanningCliResult


class FakeRunner:
    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    ) -> PlanningCliResult:
        return PlanningCliResult("ok", f"응답: {command[0]}", "", 0, 10)


def test_vib_plan_json_includes_pr5_agent_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: f"/bin/{adapter}",
    )
    monkeypatch.setattr(
        "vibelign.commands.vib_plan_cmd.SubprocessPlanningCliRunner",
        lambda: FakeRunner(),
    )

    run_vib_plan(
        Namespace(
            idea=["예약 앱"],
            template_only=False,
            output=None,
            force=False,
            language="auto",
            json=True,
            cli="claude,codex",
            agents="chloe,gio",
            save_transcript=False,
            llm_timeout_seconds=1,
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["agents_requested"] == ["chloe", "gio"]
    assert payload["agents_used"] == ["chloe", "gio"]
    assert payload["agent_statuses"] == {"chloe": "ok", "gio": "ok"}
    assert payload["adapter"] == "claude"
    assert payload["persona_id"] == "chloe"
