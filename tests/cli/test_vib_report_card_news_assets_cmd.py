from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal, TypedDict

import pytest
from pydantic import BaseModel, ConfigDict

from vibelign.commands.vib_report_card_news_cmd import run_vib_report_card_news

ApprovedValue = bool | Literal["false"]


class _SourceRefJson(TypedDict):
    source_plan_path: str
    section: int
    block: int
    heading: str


class _ImageJson(TypedDict):
    provider: str
    asset_path: str
    prompt: str
    generated: bool


class _CardJson(TypedDict):
    id: str
    title: str
    body: str
    caption: str
    visual_prompt: str
    negative_prompt: str
    source_refs: list[_SourceRefJson]
    image: _ImageJson
    approved: ApprovedValue


class _PayloadJson(TypedDict):
    schema_version: str
    status: Literal["ready"]
    provider: str
    cards: list[_CardJson]
    assets: list[_ImageJson]


class _CliJson(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    ok: bool
    html_path: str = ""
    json_path: str = ""


class _ExportImageJson(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    asset_path: str = ""
    generated: bool = False


class _ExportCardJson(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    image: _ExportImageJson


class _ExportJson(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    cards: list[_ExportCardJson]


@dataclass(frozen=True, slots=True)
class _CardNewsArgs:
    payload: str
    json: bool


def _card(card_id: str, *, approved: ApprovedValue, asset_path: str = "") -> _CardJson:
    return {
        "id": card_id,
        "title": "개요",
        "body": "보고서 핵심 메시지를 요약합니다.",
        "caption": "출처: 개요",
        "visual_prompt": "2D business comic illustration, no readable text in image",
        "negative_prompt": "readable text",
        "source_refs": [{"source_plan_path": "plans/demo.md", "section": 0, "block": 0, "heading": "개요"}],
        "image": {
            "provider": "provider-neutral-draft",
            "asset_path": asset_path,
            "prompt": "2D business comic illustration, no readable text in image",
            "generated": False,
        },
        "approved": approved,
    }


def _card_with_text(card_id: str, title: str, body: str, visual_prompt: str) -> _CardJson:
    card = _card(card_id, approved=True)
    card["title"] = title
    card["body"] = body
    card["visual_prompt"] = visual_prompt
    card["image"]["prompt"] = visual_prompt
    return card


def _write_payload(path: Path, cards: list[_CardJson]) -> Path:
    data: _PayloadJson = {
        "schema_version": "report-visual-cards-v1",
        "status": "ready",
        "provider": "provider-neutral-draft",
        "cards": cards,
        "assets": [],
    }
    _ = path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _args(payload_path: Path) -> _CardNewsArgs:
    return _CardNewsArgs(payload=str(payload_path), json=True)


def _read_json(stdout: str) -> _CliJson:
    return _CliJson.model_validate_json(stdout)


def _read_export(path: Path) -> _ExportJson:
    return _ExportJson.model_validate_json(path.read_text(encoding="utf-8"))


def test_report_card_news_generates_svg_asset_for_empty_image_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = _write_payload(tmp_path / "cards.json", [_card("card-1", approved=True)])

    run_vib_report_card_news(_args(payload))

    out = _read_json(capsys.readouterr().out)
    html = Path(out.html_path).read_text(encoding="utf-8")
    exported = _read_export(Path(out.json_path))
    generated_asset = tmp_path / exported.cards[0].image.asset_path
    assert '<img class="panel-visual-img"' in html
    assert generated_asset.exists()
    assert 'data-schema="report-card-news-svg-asset-v1"' in generated_asset.read_text(encoding="utf-8")
    assert exported.cards[0].image.generated is True


def test_report_card_news_keeps_existing_project_image_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    image = tmp_path / ".vibelign" / "reports" / "card-news" / "assets" / "card-1.png"
    image.parent.mkdir(parents=True)
    _ = image.write_bytes(b"fake-png")
    payload = _write_payload(tmp_path / "cards.json", [_card("card-1", approved=True, asset_path=str(image))])

    run_vib_report_card_news(_args(payload))

    out = _read_json(capsys.readouterr().out)
    html = Path(out.html_path).read_text(encoding="utf-8")
    assert '<figure class="sketch">' in html
    assert '<img class="panel-visual-img" src="assets/card-1.png"' in html
    assert html.index('<figure class="sketch">') < html.index('<ul class="points">')


def test_report_card_news_svg_assets_change_with_visual_prompt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    alarm_card = _card_with_text(
        "card-1",
        "일정 알림",
        "캘린더 날짜마다 반복 알림을 보내고 할일 목록을 확인합니다.",
        "mobile reminder app with calendar checklist notification",
    )
    payment_card = _card_with_text(
        "card-2",
        "결제 정책",
        "구독 가격과 환불 정책을 보안 인증 뒤에 확인합니다.",
        "subscription payment policy security screen",
    )
    payload = _write_payload(tmp_path / "cards.json", [alarm_card, payment_card])

    run_vib_report_card_news(_args(payload))

    out = _read_json(capsys.readouterr().out)
    html = Path(out.html_path).read_text(encoding="utf-8")
    exported = _read_export(Path(out.json_path))
    asset_texts = [
        (tmp_path / card.image.asset_path).read_text(encoding="utf-8")
        for card in exported.cards
    ]
    assert any('data-sketch-symbols="calendar,bell,checklist"' in text for text in asset_texts)
    assert any('data-sketch-symbols="wallet,lock,document"' in text for text in asset_texts)
    assert "결제" in html
