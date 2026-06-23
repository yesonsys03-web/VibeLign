"""Tests for card_news_mode="poster" runtime branch (Task C4)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

import pytest

from vibelign.commands.vib_report_cmd import run_vib_report
from vibelign.core.planning_cli import cli_adapters

PLAN_MD = (
    "# 예약 앱\n\n"
    "## 한 줄 목표\n"
    "미용실 예약 앱.\n\n"
    "## 핵심 기능\n"
    "- 예약 캘린더\n"
    "- 알림 문자\n"
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class _ReportArgs:
    """Minimal args fixture matching vib_report_runtime expectations."""

    def __init__(self, plan: str) -> None:
        self.plan = plan
        self.type = "work"
        self.format = "html"
        self.output: str | None = None
        self.force = False
        self.date: str | None = "2026-06-15"
        self.json = True
        self.polish = False
        self.cli = "auto"
        self.emit_model = False
        self.assist_missing = False
        self.visual_cards = True
        self.visual_card_cli = "opencode"
        self.card_news_mode = "poster"
        self.reject_blocks: str | None = None
        self.polish_key: str | None = None
        self.theme = "classic"
        self.title_font_size: int | None = None
        self.heading_font_size: int | None = None
        self.body_font_size: int | None = None
        self.meta_font_size: int | None = None
        self.heading_font: str | None = None
        self.body_font: str | None = None
        self.author = ""
        self.page_numbers = True


# ---------------------------------------------------------------------------
# Fake CLI runner — same pattern as test_vib_report_visual_cards_draft_assets_cmd.py
# ---------------------------------------------------------------------------

_POSTER_HTML = (
    "<html><head><style>body{font-family:sans-serif}</style></head>"
    "<body><h1>카드뉴스</h1></body></html>"
)


def _fake_build_command(provider: str, prompt: str) -> list[str]:
    return ["fake", provider, prompt]


def _fake_run(
    _self: cli_adapters.SubprocessPlanningCliRunner,
    command: list[str],
    *,
    cwd: Path,
    input_text: str,
    timeout_seconds: int,
) -> cli_adapters.PlanningCliResult:
    _ = cwd
    _ = input_text
    _ = timeout_seconds
    prompt = command[2]
    # Draft call — returns card JSON
    if prompt.startswith("한국어 보고서 카드뉴스 초안"):
        stdout = json.dumps(
            {
                "cards": [
                    {
                        "title": "예약 흐름",
                        "body": "예약 캘린더와 알림 문자를 한 장으로 설명합니다.",
                        "caption": "출처: 핵심 기능",
                        "visual_prompt": "calendar booking flow with notification message bubbles, no readable text in image",
                    }
                ]
            },
            ensure_ascii=False,
        )
    # Poster HTML generation call (prompt starts with "아래 스토리보드")
    elif prompt.startswith("아래 스토리보드"):
        stdout = _POSTER_HTML
    # SVG asset generation call (batch or single: starts with "Create")
    elif prompt.startswith("Create"):
        stdout = '<svg viewBox="0 0 320 150" data-model-asset="yes"><rect width="320" height="150"/></svg>'
    else:
        raise ValueError(f"unexpected prompt: {prompt[:80]}")
    return cli_adapters.PlanningCliResult(status="ok", stdout=stdout, stderr="", exit_code=0, duration_ms=1)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_poster_mode_includes_poster_html(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """poster mode with a real CLI provider → JSON payload includes card_news_poster."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _fake_run)

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))
    run_vib_report(args)

    raw: JsonValue = json.loads(capsys.readouterr().out)
    assert isinstance(raw, dict)
    assert raw["ok"] is True
    assert "card_news_poster" in raw, "card_news_poster key must be in JSON payload for poster mode"
    poster = raw["card_news_poster"]
    assert isinstance(poster, dict)
    assert poster["source"] in ("llm", "fallback"), f"unexpected source: {poster['source']}"
    assert "<html" in poster["html"].lower(), "poster html must contain <html"


def test_per_card_mode_omits_poster_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """per-card mode → no card_news_poster key in JSON payload."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _fake_run)

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))
    args.card_news_mode = "per-card"
    run_vib_report(args)

    raw: JsonValue = json.loads(capsys.readouterr().out)
    assert isinstance(raw, dict)
    assert raw["ok"] is True
    assert "card_news_poster" not in raw, "card_news_poster must NOT appear in per-card mode"


def test_poster_mode_with_local_provider_omits_poster_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """poster mode but local provider (no LLM) → no card_news_poster key."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _fake_run)

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))
    args.card_news_mode = "poster"
    args.visual_card_cli = "local"
    run_vib_report(args)

    raw: JsonValue = json.loads(capsys.readouterr().out)
    assert isinstance(raw, dict)
    assert raw["ok"] is True
    assert "card_news_poster" not in raw, "card_news_poster must NOT appear when provider is local"


def test_poster_mode_emits_progress_stages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """poster mode with CLI provider → stderr contains stage=draft, stage=assets, stage=poster."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _fake_run)

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))
    run_vib_report(args)

    err = capsys.readouterr().err
    assert "[progress] step=report-cards stage=draft" in err
    assert "[progress] step=report-cards stage=assets" in err
    assert "[progress] step=report-cards stage=poster" in err


def _recording_run_factory(
    seen_prompts: list[str],
):
    def _run(
        _self: cli_adapters.SubprocessPlanningCliRunner,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    ) -> cli_adapters.PlanningCliResult:
        seen_prompts.append(command[2])
        return _fake_run(_self, command, cwd=cwd, input_text=input_text, timeout_seconds=timeout_seconds)

    return _run


def test_poster_mode_skips_svg_asset_generation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Poster mode redraws every card from text and never consumes the per-card SVG assets,
    so the expensive SVG asset-generation CLI call must be skipped entirely."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    seen_prompts: list[str] = []
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _recording_run_factory(seen_prompts))

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))  # card_news_mode == "poster"
    run_vib_report(args)

    raw: JsonValue = json.loads(capsys.readouterr().out)
    assert isinstance(raw, dict)
    assert raw["ok"] is True
    assert "card_news_poster" in raw, "poster must still be produced in poster mode"
    svg_calls = [p for p in seen_prompts if p.startswith("Create")]
    assert svg_calls == [], f"poster mode must not generate per-card SVG assets, got: {svg_calls}"


def test_per_card_mode_still_generates_svg_assets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The asset-skip is poster-only: per-card mode must still materialize per-card SVGs."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    seen_prompts: list[str] = []
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _recording_run_factory(seen_prompts))

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))
    args.card_news_mode = "per-card"
    run_vib_report(args)

    raw: JsonValue = json.loads(capsys.readouterr().out)
    assert isinstance(raw, dict)
    assert raw["ok"] is True
    svg_calls = [p for p in seen_prompts if p.startswith("Create")]
    assert svg_calls, "per-card mode must still generate per-card SVG assets"


def _card_news_events(stderr: str) -> list[dict[str, JsonValue]]:
    events: list[dict[str, JsonValue]] = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("type") == "card_news_event":
            events.append(obj)
    return events


def test_poster_mode_emits_draft_storyboard_event(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Poster mode streams the draft storyboard on stderr so the GUI has the cards immediately.
    No poster_draft placeholder is emitted (the in-app preview shows only the progress bar)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _fake_run)

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    run_vib_report(_ReportArgs(plan=str(plan)))  # poster mode

    events = _card_news_events(capsys.readouterr().err)
    kinds = [e["kind"] for e in events]
    assert "draft" in kinds, f"expected a draft event, got {kinds}"
    assert "poster_draft" not in kinds, "poster_draft placeholder was removed"

    draft = next(e for e in events if e["kind"] == "draft")
    assert isinstance(draft["visual_cards"], dict)
    assert draft["visual_cards"]["status"] == "ready"


def test_per_card_mode_emits_draft_event_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per-card mode streams the draft storyboard but no poster_draft (no poster stage)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _fake_run)

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))
    args.card_news_mode = "per-card"
    run_vib_report(args)

    kinds = [e["kind"] for e in _card_news_events(capsys.readouterr().err)]
    assert "draft" in kinds
    assert "poster_draft" not in kinds


def _fake_run_draft_unparseable(
    _self: cli_adapters.SubprocessPlanningCliRunner,
    command: list[str],
    *,
    cwd: Path,
    input_text: str,
    timeout_seconds: int,
) -> cli_adapters.PlanningCliResult:
    prompt = command[2]
    if prompt.startswith("한국어 보고서 카드뉴스 초안"):
        # Model returns prose instead of JSON — draft parse fails (VisualCardsCliError).
        return cli_adapters.PlanningCliResult(
            status="ok", stdout="죄송하지만 JSON을 만들 수 없습니다. 설명만 드릴게요.", stderr="", exit_code=0, duration_ms=1
        )
    return _fake_run(_self, command, cwd=cwd, input_text=input_text, timeout_seconds=timeout_seconds)


def test_draft_parse_failure_degrades_instead_of_hard_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unparseable draft response must NOT hard-fail; generation degrades to base cards."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", _fake_run_draft_unparseable)

    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    args = _ReportArgs(plan=str(plan))
    run_vib_report(args)

    raw: JsonValue = json.loads(capsys.readouterr().out)
    assert isinstance(raw, dict)
    assert raw["ok"] is True  # no hard failure despite the unparseable draft
    assert "visual_cards" in raw
    # Poster mode still designs its poster from the (degraded) base cards.
    assert "card_news_poster" in raw
