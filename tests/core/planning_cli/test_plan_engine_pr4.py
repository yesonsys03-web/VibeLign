from pathlib import Path

from vibelign.core.planning_cli.cli_adapters import PlanningCliResult
from vibelign.core.planning_cli.engine import create_planning_with_persona
from vibelign.core.planning_cli.models import PlanningInput


class FakeRunner:
    def __init__(self, result: PlanningCliResult) -> None:
        self.result = result
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
        return self.result


def test_engine_appends_persona_review_on_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.resolve_cli_executable",
        lambda _adapter: "/usr/local/bin/codex",
    )
    monkeypatch.setattr(
        "vibelign.core.planning_cli.engine.build_codex_command",
        lambda prompt: ["/usr/local/bin/codex", "exec", prompt],
    )
    runner = FakeRunner(
        PlanningCliResult(
            status="ok",
            stdout="요구사항을 더 작게 나누면 좋아요.",
            stderr="",
            exit_code=0,
            duration_ms=10,
        )
    )

    result = create_planning_with_persona(
        tmp_path,
        PlanningInput(idea="예약 앱"),
        runner=runner,
    )

    assert result.adapter == "codex"
    assert result.persona_id == "gio"
    assert result.llm_status == "ok"
    assert result.fallback_reason is None
    assert "## 지오의 검토" in result.markdown
    assert (tmp_path / result.output_path).read_text(encoding="utf-8") == result.markdown


def test_engine_falls_back_when_cli_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.engine.build_codex_command",
        lambda _prompt: None,
    )

    result = create_planning_with_persona(tmp_path, PlanningInput(idea="예약 앱"))

    assert result.llm_status == "not_installed"
    assert result.fallback_reason == "cli_unavailable_template_only"
    assert "## 지오의 검토" not in result.markdown


def test_engine_rejects_forbidden_terms_from_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "vibelign.core.planning_cli.engine.build_codex_command",
        lambda prompt: ["/usr/local/bin/codex", "exec", prompt],
    )
    runner = FakeRunner(
        PlanningCliResult(
            status="ok",
            stdout="target_anchor를 써야 합니다.",
            stderr="",
            exit_code=0,
            duration_ms=10,
        )
    )

    result = create_planning_with_persona(
        tmp_path,
        PlanningInput(idea="예약 앱"),
        runner=runner,
    )

    assert result.llm_status == "bad_output"
    assert result.fallback_reason == "cli_unavailable_template_only"
    assert "target_anchor" not in (tmp_path / result.output_path).read_text(encoding="utf-8")
