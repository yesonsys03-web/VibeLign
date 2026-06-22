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
