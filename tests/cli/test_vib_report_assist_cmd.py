import json
from dataclasses import dataclass
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


@dataclass(slots=True)
class ReportArgsStub:
    plan: str
    type: str = "work"
    format: str = "html"
    output: str | None = None
    force: bool = False
    date: str | None = "2026-06-15"
    json: bool = False
    polish: bool = False
    cli: str = "auto"
    emit_model: bool = False
    assist_missing: bool = False
    visual_cards: bool = False
    reject_blocks: str | None = None
    polish_key: str | None = None
    theme: str = "classic"
    title_font_size: int | None = None
    heading_font_size: int | None = None
    body_font_size: int | None = None
    meta_font_size: int | None = None
    heading_font: str | None = None
    body_font: str | None = None
    author: str = ""
    page_numbers: bool = True


def _args(
    plan_path: Path,
    *,
    want_json: bool = False,
    assist_missing: bool = False,
    report_type: str = "work",
    cli: str = "auto",
) -> ReportArgsStub:
    return ReportArgsStub(
        plan=str(plan_path),
        json=want_json,
        assist_missing=assist_missing,
        type=report_type,
        cli=cli,
    )


def test_report_subcommand_accepts_assist_missing_flag():
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["report", "plan.md", "--assist-missing", "--cli", "codex", "--json"])
    assert ns.assist_missing is True
    assert ns.cli == "codex"


def test_report_assist_missing_json_returns_user_questions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "quality_sparse.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    run_vib_report(_args(plan, want_json=True, assist_missing=True, report_type="proposal"))

    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["assistance"]["schema_version"] == "report-assist-v1"
    assert out["assistance"]["status"] == "needs_user_input"
    assert [item for item in out["assistance"]["suggestions"] if item["kind"] == "user_question"]
    assert [item for item in out["assistance"]["suggestions"] if item["kind"] != "user_question"]


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

    run_vib_report(_args(plan, want_json=True, assist_missing=True, report_type="work"))

    out = json.loads(capsys.readouterr().out)
    refs = [
        ref
        for item in out["assistance"]["suggestions"]
        for ref in item["source_refs"]
    ]
    assert out["ok"] is True
    assert len(refs) <= 15
    assert any(900 <= ref["start_line"] <= 1100 for ref in refs)
