import json
import re
from argparse import Namespace
from pathlib import Path

import pytest

from vibelign.commands.vib_report_cmd import run_vib_report


def _args(plan_path: Path, **over) -> Namespace:
    base = dict(
        plan=str(plan_path),
        type="work",
        format="html",
        output=None,
        force=False,
        date="2026-06-15",
        json=False,
        polish=False,
        cli="auto",
        assist_missing=False,
        visual_cards=False,
    )
    base.update(over)
    return Namespace(**base)


def test_report_subcommand_accepts_visual_cards_flag():
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["report", "plan.md", "--visual-cards", "--json"])
    assert ns.visual_cards is True


def test_report_visual_cards_json_returns_optional_sidecar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    fixture = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "reporting_cli"
        / "quality_complete.md"
    )
    plan = tmp_path / "quality_complete.md"
    plan.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    run_vib_report(_args(plan, json=True, type="proposal", visual_cards=True))

    out = json.loads(capsys.readouterr().out)
    cards = out["visual_cards"]["cards"]
    card_text = "\n".join(f"{card['title']}\n{card['body']}" for card in cards)
    assert out["ok"] is True
    assert 3 <= len(cards) <= 6
    assert out["visual_cards"]["provider"] == "provider-neutral-draft"
    assert all(card["source_refs"] for card in cards)
    assert all("no readable text in image" in card["visual_prompt"] for card in cards)
    assert all(re.search(r"[가-힣]", card["visual_prompt"]) is None for card in cards)
    assert all(card["image"]["provider"] == "provider-neutral-draft" for card in cards)
    assert all(card["image"]["asset_path"] == "" for card in cards)
    assert all("fake://" not in card["image"]["asset_path"] for card in cards)
    assert all("예약" not in card["visual_prompt"] for card in cards)
    assert "리스크" in card_text
    assert "다음 액션" in card_text
