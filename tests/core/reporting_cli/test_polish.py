from dataclasses import dataclass

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.polish import polish_report_model, polish_try_order


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
