import json
from pathlib import Path

from vibelign.core.planning_cli.cli_adapters import PlanningCliResult
from vibelign.core.planning_cli.models import PlanningInput
from vibelign.core.planning_cli.orchestrator import (
    append_planning_with_agents,
    create_planning_with_agents,
)


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
    assert runner.commands[1][:2] == ["/bin/agy", "-p"]


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


def test_orchestrator_appends_followup_to_existing_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: f"/bin/{adapter}",
    )
    plan_path = tmp_path / "plans" / "app.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("# 앱\n## 한 줄 목표\n앱 만들기\n", encoding="utf-8")
    runner = FakeRunner(
        [
            PlanningCliResult("ok", "레이어 선택 흐름부터 정하세요.", "", 0, 10),
        ]
    )

    result = append_planning_with_agents(
        tmp_path,
        output_path="plans/app.md",
        message="PSD 라인 레이어 익스포트 앱으로 다듬어줘",
        agents_choice="chloe",
        runner=runner,
    )

    assert result.output_path == "plans/app.md"
    assert result.agents_requested == ("chloe",)
    assert result.agents_used == ("chloe",)
    assert "## 클로이의 설계" in result.markdown
    assert "레이어 선택 흐름부터 정하세요." in plan_path.read_text(encoding="utf-8")


def test_orchestrator_saves_opt_in_transcripts_as_turn_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: f"/bin/{adapter}",
    )
    runner = FakeRunner(
        [
            PlanningCliResult("ok", "클로이 초안입니다.", "", 0, 10),
            PlanningCliResult("ok", "지오 검토입니다.", "", 0, 10),
        ]
    )

    result = create_planning_with_agents(
        tmp_path,
        PlanningInput(idea="@chloe @gio 예약 앱"),
        runner=runner,
        save_transcript=True,
    )

    turns_dir = tmp_path / ".vibelign" / "planning" / result.session_id / "turns"
    assert (turns_dir / "turn_001_claude.md").read_text(encoding="utf-8") == "클로이 초안입니다."
    assert (turns_dir / "turn_002_codex.md").read_text(encoding="utf-8") == "지오 검토입니다."
    assert not (tmp_path / ".vibelign" / "planning" / result.session_id / "transcripts").exists()


def test_orchestrator_updates_session_json_with_agent_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: f"/bin/{adapter}",
    )
    long_response = " ".join(["클로이 초안입니다."] * 40)
    # chloe: claude → ok (1 result)
    # gio: codex→timeout, claude→timeout, agy→timeout, opencode→timeout (4 results)
    # fallback exhausts all providers; last adapter recorded is "opencode"
    runner = FakeRunner(
        [
            PlanningCliResult("ok", long_response, "", 0, 10),
            PlanningCliResult("timeout", "지오 일부 응답입니다.", "", None, 10),
            PlanningCliResult("timeout", "", "", None, 10),
            PlanningCliResult("timeout", "", "", None, 10),
            PlanningCliResult("timeout", "", "", None, 10),
        ]
    )

    result = create_planning_with_agents(
        tmp_path,
        PlanningInput(idea="@chloe @gio 예약 앱"),
        runner=runner,
    )

    session_path = tmp_path / ".vibelign" / "planning" / result.session_id / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    assert session["agents_requested"] == ["chloe", "gio"]
    assert session["agents_used"] == ["chloe"]
    assert session["agent_statuses"] == {"chloe": "ok", "gio": "timeout"}
    assert session["runs"][0] == {
        "run_id": "run_chloe_001",
        "turn_id": "turn_001",
        "persona_id": "chloe",
        "cli_id": "claude",
        "status": "ok",
        "summary": session["runs"][0]["summary"],
    }
    assert session["runs"][1]["run_id"] == "run_gio_002"
    assert session["runs"][1]["turn_id"] == "turn_002"
    # Under fallback, gio tries codex→timeout, claude→timeout, agy→timeout, opencode→timeout.
    # The run metadata captures the last adapter attempted ("opencode") and final status.
    assert session["runs"][1]["cli_id"] == "opencode"
    assert session["runs"][1]["status"] == "timeout"
    assert len(session["runs"][0]["summary"]) < len(long_response)
    assert long_response not in session_path.read_text(encoding="utf-8")


def test_orchestrator_falls_back_when_preferred_not_installed(tmp_path, monkeypatch):
    # claude 만 미설치, 나머지는 설치된 것으로
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: None if adapter == "claude" else f"/bin/{adapter}",
    )
    runner = FakeRunner([PlanningCliResult("ok", "대체 설계입니다.", "", 0, 10)])

    result = create_planning_with_agents(
        tmp_path,
        PlanningInput(idea="@chloe 예약 앱"),
        runner=runner,
    )

    # chloe 기본 provider 는 claude(미설치) → 폴백으로 codex 가 답함
    assert result.agents_used == ("chloe",)
    assert result.agent_statuses["chloe"] == "ok"
    assert runner.commands[0][0] == "/bin/codex"


def test_orchestrator_falls_back_on_runtime_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: f"/bin/{adapter}",
    )
    # 1순위(claude) 는 로그인 안 됨, 2순위(codex) 는 ok
    runner = FakeRunner(
        [
            PlanningCliResult("not_logged_in", "", "not logged in", 1, 10),
            PlanningCliResult("ok", "코덱스 설계입니다.", "", 0, 10),
        ]
    )

    result = create_planning_with_agents(
        tmp_path,
        PlanningInput(idea="@chloe 예약 앱"),
        runner=runner,
    )

    assert result.agents_used == ("chloe",)
    assert result.agent_statuses["chloe"] == "ok"
    assert runner.commands[0][0] == "/bin/claude"
    assert runner.commands[1][0] == "/bin/codex"


def test_orchestrator_skips_disabled_persona(tmp_path, monkeypatch):
    from vibelign.core.planning_cli.planning_config import PersonaConfig

    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda adapter: f"/bin/{adapter}",
    )
    monkeypatch.setattr(
        "vibelign.core.planning_cli.orchestrator.load_persona_config",
        lambda: {"gio": PersonaConfig(enabled=False, provider=None)},
    )
    runner = FakeRunner([PlanningCliResult("ok", "클로이 설계입니다.", "", 0, 10)])

    result = create_planning_with_agents(
        tmp_path,
        PlanningInput(idea="@chloe @gio 예약 앱"),
        runner=runner,
    )

    assert "gio" not in result.agents_used
    assert result.agents_used == ("chloe",)
