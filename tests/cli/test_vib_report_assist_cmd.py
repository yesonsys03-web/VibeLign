import json
from argparse import Namespace
from pathlib import Path

import pytest

from vibelign.commands.vib_report_cmd import run_vib_report

PLAN_MD = """# 예약 앱

## 한 줄 목표
미용실 예약 앱.

## 핵심 기능
- 예약 캘린더
- 알림 문자
"""


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


def test_report_subcommand_accepts_assist_missing_flag():
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["report", "plan.md", "--assist-missing", "--json"])
    assert ns.assist_missing is True


def test_report_assist_missing_json_returns_user_questions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "quality_sparse.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    run_vib_report(_args(plan, json=True, assist_missing=True, type="proposal"))

    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["assistance"]["schema_version"] == "report-assist-v1"
    assert out["assistance"]["status"] == "needs_user_input"
    assert [item for item in out["assistance"]["suggestions"] if item["kind"] == "user_question"]


def test_report_assist_missing_long_json_keeps_chunk_refs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "quality_long_2000.md"
    fixture = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "reporting_cli"
        / "quality_long_2000.md"
    )
    plan.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    run_vib_report(_args(plan, json=True, assist_missing=True, type="work"))

    out = json.loads(capsys.readouterr().out)
    refs = [
        ref
        for item in out["assistance"]["suggestions"]
        for ref in item["source_refs"]
    ]
    assert out["ok"] is True
    assert len(refs) <= 15
    assert any(900 <= ref["start_line"] <= 1100 for ref in refs)
