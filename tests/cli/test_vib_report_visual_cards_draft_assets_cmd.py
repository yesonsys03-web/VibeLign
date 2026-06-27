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


class ReportArgsFixture:
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


def test_report_visual_card_cli_draft_materializes_model_assets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_adapters, "build_cli_command", fake_build_command)
    monkeypatch.setattr(cli_adapters.SubprocessPlanningCliRunner, "run", fake_run)
    plan = tmp_path / "plan.md"
    _ = plan.write_text(PLAN_MD, encoding="utf-8")

    run_vib_report(ReportArgsFixture(plan=str(plan)))

    raw_payload: JsonValue = json.loads(capsys.readouterr().out)
    payload = expect_dict(raw_payload)
    visual_cards = expect_dict(payload["visual_cards"])
    card = expect_dict(expect_list(visual_cards["cards"])[0])
    image = expect_dict(card["image"])
    asset_path = expect_str(image["asset_path"])
    asset = tmp_path / asset_path
    assert image["provider"] == "opencode"
    assert image["generated"] is True
    assert asset.exists()
    assert 'data-model-asset="yes"' in asset.read_text(encoding="utf-8")


def fake_build_command(provider: str, prompt: str) -> list[str]:
    return ["fake", provider, prompt]


def fake_run(
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
    else:
        stdout = '<svg viewBox="0 0 320 150" data-model-asset="yes"><rect width="320" height="150"/></svg>'
    return cli_adapters.PlanningCliResult(status="ok", stdout=stdout, stderr="", exit_code=0, duration_ms=1)


def expect_dict(value: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(value, dict)
    return value


def expect_list(value: JsonValue) -> list[JsonValue]:
    assert isinstance(value, list)
    return value


def expect_str(value: JsonValue) -> str:
    assert isinstance(value, str)
    return value
