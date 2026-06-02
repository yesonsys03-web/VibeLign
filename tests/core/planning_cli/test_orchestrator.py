from pathlib import Path

from vibelign.core.planning_cli.cli_adapters import PlanningCliResult
from vibelign.core.planning_cli.models import PlanningInput
from vibelign.core.planning_cli.orchestrator import create_planning_with_agents


class FakeRunner:
    def __init__(self, results: list[PlanningCliResult]) -> None:
        self._results = results
        self.commands: list[list[str]] = []

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    ) -> PlanningCliResult:
        self.commands.append(command)
        return self._results.pop(0)


def test_orchestrator_runs_requested_personas_in_fixed_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: f"/bin/{adapter}",
    )
    runner = FakeRunner(
        [
            PlanningCliResult("ok", "지오 검토입니다.", "", 0, 10),
            PlanningCliResult("ok", "미나 탐색입니다.", "", 0, 10),
        ]
    )

    result = create_planning_with_agents(
        tmp_path,
        PlanningInput(idea="@mina @지오 자동 스크린샷 앱"),
        runner=runner,
    )

    assert result.agents_requested == ("gio", "mina")
    assert result.agents_used == ("gio", "mina")
    assert result.agent_statuses == {"gio": "ok", "mina": "ok"}
    assert result.fallback_reason is None
    assert result.markdown.startswith("# 자동 스크린샷 앱")
    assert "## 지오의 검토" in result.markdown
    assert "## 미나의 탐색" in result.markdown
    assert runner.commands[0][:2] == ["/bin/codex", "exec"]
    assert runner.commands[1][:2] == ["/bin/agy", "--print"]


def test_orchestrator_keeps_template_when_all_agents_fail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda _adapter: None,
    )

    result = create_planning_with_agents(
        tmp_path,
        PlanningInput(idea="@chloe @gio 예약 앱"),
    )

    assert result.agents_requested == ("chloe", "gio")
    assert result.agents_used == ()
    assert result.agent_statuses == {
        "chloe": "not_installed",
        "gio": "not_installed",
    }
    assert result.fallback_reason == "cli_unavailable_template_only"
    assert "## 클로이의 설계" not in result.markdown
    assert (tmp_path / result.output_path).read_text(encoding="utf-8") == result.markdown
