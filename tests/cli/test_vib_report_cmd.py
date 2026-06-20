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


def test_report_writes_html_and_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    run_vib_report(_args(plan, json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["report_type"] == "work"
    out_path = Path(payload["path"])
    assert out_path.exists()
    html = out_path.read_text(encoding="utf-8")
    assert "업무 보고" in html
    assert "<li>예약 캘린더</li>" in html


def test_report_unknown_type_reports_error_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, type="nope", json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False


def test_report_unsafe_output_reports_error_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, output="../report.html", json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "project-relative" in payload["error"]


def test_report_existing_output_reports_error_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    output = tmp_path / "out" / "report.html"
    output.parent.mkdir()
    output.write_text("<old>", encoding="utf-8")

    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, output="out/report.html", json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "already exists" in payload["error"]
    assert output.read_text(encoding="utf-8") == "<old>"


def test_report_subcommand_is_registered():
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["report", "plan.md", "--type", "proposal"])
    assert ns.type == "proposal"
    assert callable(ns.func)
    assert "report" in parser.format_help()


def test_report_subcommand_keeps_type_validation_inside_command():
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["report", "plan.md", "--type", "nope", "--json"])
    assert ns.type == "nope"
    assert callable(ns.func)


def test_report_subcommand_keeps_theme_validation_inside_command(
    capsys: pytest.CaptureFixture[str],
):
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["report", "plan.md", "--theme", "not-a-theme", "--json"])
    assert ns.theme == "not-a-theme"
    with pytest.raises(SystemExit):
        parser.parse_args(["report", "--help"])
    help_text = capsys.readouterr().out
    assert "--theme THEME" in help_text
    assert "plain-indigo-balanced" not in help_text


def test_report_subcommand_accepts_font_size_options():
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(
        [
            "report",
            "plan.md",
            "--title-font-size",
            "32",
            "--heading-font-size",
            "19",
            "--body-font-size",
            "15",
            "--meta-font-size",
            "11",
        ]
    )
    assert ns.title_font_size == 32
    assert ns.heading_font_size == 19
    assert ns.body_font_size == 15
    assert ns.meta_font_size == 11


def test_report_unreadable_plan_reports_error_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"\xff\xfe \x80\x81 invalid utf-8")

    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "읽을 수 없" in payload["error"]


def test_report_docx_writes_binary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, format="docx"))
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    out = Path(payload["path"])
    assert out.suffix == ".docx"
    assert out.read_bytes()[:2] == b"PK"


def test_report_docx_graceful_when_lib_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    import vibelign.core.reporting_cli.docx_renderer as dmod
    monkeypatch.setattr(dmod, "DOCX_AVAILABLE", False)
    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True, format="docx"))
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "python-docx" in payload["error"]


def test_report_subcommand_accepts_font_options():
    from vibelign.cli.vib_cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(
        [
            "report",
            "plan.md",
            "--heading-font",
            "pretendard",
            "--body-font",
            "gowun-batang",
        ]
    )
    assert ns.heading_font == "pretendard"
    assert ns.body_font == "gowun-batang"


DOC_MD = """# 자유 문서

도입 문단.

## 배경
어떤 배경 설명.

## 항목
- 첫째
- 둘째
"""


def test_report_type_doc_renders_arbitrary_markdown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "free.md"
    doc.write_text(DOC_MD, encoding="utf-8")

    run_vib_report(_args(doc, type="doc", json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["report_type"] == "doc"
    html = Path(payload["path"]).read_text(encoding="utf-8")
    assert "배경" in html
    assert "<li>첫째</li>" in html


def test_report_type_doc_empty_file_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    doc = tmp_path / "empty.md"
    doc.write_text("   \n\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        run_vib_report(_args(doc, type="doc", json=True))
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "내보낼 내용" in payload["error"]
