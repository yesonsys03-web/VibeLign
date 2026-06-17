from dataclasses import dataclass

import pytest

from vibelign.core.reporting_cli import polish as polish_mod
from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.polish import (
    polish_report_model,
    polish_report_model_with_guards,
    polish_try_order,
)


@dataclass
class FakeResult:
    status: str
    stdout: str


class FakeRunner:
    """SubprocessPlanningCliRunner 대역. attempts 에 (adapter, prompt) 기록."""

    def __init__(self, script):
        self.script = script  # dict: adapter -> FakeResult
        self.attempts = []

    def run(self, command, *, cwd, input_text, timeout_seconds):
        adapter = command[0]
        self.attempts.append(adapter)
        return self.script.get(adapter, FakeResult("not_installed", ""))


@pytest.fixture(autouse=True)
def _stub_build_cli_command(monkeypatch):
    # 실제 build_cli_command 은 전체 경로+서브커맨드를 반환하지만, 테스트는 adapter 식별만
    # 필요하다. command[0]=adapter 로 스텁해 FakeRunner 가 adapter 를 식별하게 한다.
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.build_cli_command",
        lambda adapter, prompt: [adapter, prompt],
    )


def _model():
    return ReportModel(
        title="예약 앱",
        report_type="work",
        date="2026-06-16",
        sections=[
            Section("개요", [Block(kind="summary", text="예약 앱 MVP")]),
            Section("핵심 내용", [Block(kind="bullets", items=["캘린더", "알림"])]),
            Section("배경", [Block(kind="paragraph", text="전화 예약 누락이 잦음")]),
        ],
    )


def test_try_order_auto_is_free_only_no_claude():
    order = polish_try_order("auto")
    assert "claude" not in order
    assert order[0] == "codex"  # design §6: codex → opencode → agy


def test_try_order_explicit_claude_allowed():
    # 명시 opt-in 일 때만 claude
    assert polish_try_order("claude")[0] == "claude"


def test_polish_rewrites_paragraph_and_summary_keeps_bullets():
    runner = FakeRunner({"codex": FakeResult("ok", "다듬은 문장")})
    out = polish_report_model(_model(), provider="auto", runner=runner)
    # summary/paragraph 텍스트가 다듬어짐
    assert out.sections[0].blocks[0].text == "다듬은 문장"
    assert out.sections[2].blocks[0].text == "다듬은 문장"
    # bullets 는 MVP 에서 손대지 않음
    assert out.sections[1].blocks[0].items == ["캘린더", "알림"]
    # claude 는 시도조차 안 됨
    assert "claude" not in runner.attempts


def test_polish_failure_keeps_original_text():
    runner = FakeRunner({})  # 모든 provider not_installed
    out = polish_report_model(_model(), provider="auto", runner=runner)
    assert out.sections[2].blocks[0].text == "전화 예약 누락이 잦음"  # 원문 유지


def test_polish_falls_back_to_next_free_provider():
    runner = FakeRunner({
        "codex": FakeResult("timeout", ""),
        "opencode": FakeResult("ok", "오픈코드 다듬음"),
    })
    out = polish_report_model(_model(), provider="auto", runner=runner)
    assert out.sections[2].blocks[0].text == "오픈코드 다듬음"
    assert "claude" not in runner.attempts


def test_polish_returns_new_model_does_not_mutate_input():
    original = _model()
    runner = FakeRunner({"codex": FakeResult("ok", "X")})
    out = polish_report_model(original, provider="auto", runner=runner)
    assert original.sections[0].blocks[0].text == "예약 앱 MVP"  # 입력 불변
    assert out is not original


def test_polish_runs_build_cli_command_output_verbatim(monkeypatch):
    # 회귀 가드: polish 는 build_cli_command 의 실제 명령(경로+서브커맨드)을 그대로 실행해야 한다.
    # 버그 버전([adapter, prompt] 로 대체)이면 이 테스트가 실패한다.
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.build_cli_command",
        lambda adapter, prompt: [f"/bin/{adapter}", "exec", prompt],
    )
    captured = {}

    class CaptRunner:
        def run(self, command, *, cwd, input_text, timeout_seconds):
            captured["cmd"] = command
            return FakeResult("ok", "x")

    polish_report_model(_model(), provider="codex", runner=CaptRunner())
    assert captured["cmd"][0] == "/bin/codex"  # 전체 경로 보존
    assert "exec" in captured["cmd"]  # 서브커맨드 보존


def test_polish_prompt_forbids_changing_numbers(monkeypatch):
    captured = {}

    def fake_build(adapter, prompt):
        captured["prompt"] = prompt
        return None  # 미설치로 처리 → 호출만 캡처

    monkeypatch.setattr(polish_mod.cli_adapters, "build_cli_command", fake_build)
    polish_mod.polish_block_text(
        "신규 회원 50% 증가", provider="codex",
        runner=polish_mod.cli_adapters.SubprocessPlanningCliRunner(), root=None, timeout_seconds=1,
    )
    assert "숫자" in captured["prompt"]
    assert "과장" in captured["prompt"]


class _NumberDroppingRunner:
    """summary 의 50% 를 '대폭' 으로 바꾸는(=숫자 누락) 가짜 다듬기."""

    def run(self, command, *, cwd, input_text, timeout_seconds):
        from types import SimpleNamespace

        return SimpleNamespace(status="ok", stdout="신규 회원 대폭 증가", stderr="", exit_code=0, duration_ms=1)


def test_guard_reverts_block_and_records():
    model = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="개요", blocks=[Block(kind="summary", text="신규 회원 50% 증가")])],
    )
    out, guards = polish_report_model_with_guards(
        model, provider="codex", runner=_NumberDroppingRunner(), root=None,
    )
    assert out.sections[0].blocks[0].text == "신규 회원 50% 증가"  # 원문 유지
    assert guards == [{"section": 0, "block": 0, "reason": "number_dropped", "missing": ["50"]}]
