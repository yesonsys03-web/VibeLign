import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal, TypedDict

import pytest
from pydantic import BaseModel, ConfigDict, Field

from vibelign.cli.vib_cli import build_parser
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
    error: str = ""


class _ParsedArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    payload: str
    want_json: bool = Field(alias="json")


@dataclass(frozen=True, slots=True)
class _CardNewsArgs:
    payload: str
    json: bool


def _card(card_id: str, *, approved: ApprovedValue) -> _CardJson:
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
            "asset_path": "",
            "prompt": "2D business comic illustration, no readable text in image",
            "generated": False,
        },
        "approved": approved,
    }


def _payload(path: Path, *, approved: bool) -> Path:
    data: _PayloadJson = {
        "schema_version": "report-visual-cards-v1",
        "status": "ready",
        "provider": "provider-neutral-draft",
        "cards": [_card("card-1", approved=approved)],
        "assets": [],
    }
    _ = path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _payload_with_raw_approved(path: Path, approved: Literal["false"]) -> Path:
    data: _PayloadJson = {
        "schema_version": "report-visual-cards-v1",
        "status": "ready",
        "provider": "provider-neutral-draft",
        "cards": [{**_card("card-1", approved=False), "approved": approved}],
        "assets": [],
    }
    _ = path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _args(payload_path: Path) -> _CardNewsArgs:
    return _CardNewsArgs(payload=str(payload_path), json=True)


def _read_json(stdout: str) -> _CliJson:
    return _CliJson.model_validate_json(stdout)


def test_report_card_news_subcommand_accepts_payload_path() -> None:
    parser = build_parser()
    ns = parser.parse_args(["report-card-news", "cards.json", "--json"])
    parsed = _ParsedArgs.model_validate(vars(ns))

    assert parsed.payload == "cards.json"
    assert parsed.want_json is True


def test_report_card_news_writes_json_and_html_for_approved_cards(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = _payload(tmp_path / "cards.json", approved=True)

    run_vib_report_card_news(_args(payload))

    out = _read_json(capsys.readouterr().out)
    html_path = Path(out.html_path)
    json_path = Path(out.json_path)
    assert out.ok is True
    assert html_path.exists()
    assert json_path.exists()
    assert html_path.parent == tmp_path / ".vibelign" / "reports" / "card-news"
    html = html_path.read_text(encoding="utf-8")
    assert "보고서 핵심 메시지를 요약합니다." in html
    assert "<script" not in html
    assert "http://" not in html
    assert "https://" not in html
    assert "fake://" not in html


def test_report_card_news_rejects_empty_approved_cards(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = _payload(tmp_path / "cards.json", approved=False)

    with pytest.raises(SystemExit):
        run_vib_report_card_news(_args(payload))

    out = _read_json(capsys.readouterr().out)
    assert out.ok is False
    assert "승인" in out.error
    assert not (tmp_path / ".vibelign" / "reports" / "card-news").exists()


def test_report_card_news_requires_literal_true_approval(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    payload = _payload_with_raw_approved(tmp_path / "cards.json", "false")

    with pytest.raises(SystemExit):
        run_vib_report_card_news(_args(payload))

    out = _read_json(capsys.readouterr().out)
    assert out.ok is False
    assert out.error
    assert not (tmp_path / ".vibelign" / "reports" / "card-news").exists()


def test_report_card_news_rejects_symlinked_output_dir(
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path_factory.mktemp("card-news-outside")
    reports = tmp_path / ".vibelign" / "reports"
    reports.mkdir(parents=True)
    (reports / "card-news").symlink_to(outside)
    payload = _payload(tmp_path / "cards.json", approved=True)

    with pytest.raises(SystemExit):
        run_vib_report_card_news(_args(payload))

    out = _read_json(capsys.readouterr().out)
    assert out.ok is False
    assert "프로젝트 밖" in out.error
    assert not any(outside.iterdir())


def test_report_card_news_reports_missing_payload_as_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit):
        run_vib_report_card_news(_args(tmp_path / "missing.json"))

    out = _read_json(capsys.readouterr().out)
    assert out.ok is False
    assert "payload" in out.error
