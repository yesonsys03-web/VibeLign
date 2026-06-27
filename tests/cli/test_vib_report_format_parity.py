import json
import zipfile
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
    )
    base.update(over)
    return Namespace(**base)


def _copy_quality_complete_fixture(tmp_path: Path) -> Path:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "reporting_cli"
        / "quality_complete.md"
    )
    plan = tmp_path / "quality_complete.md"
    plan.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    return plan


def _package_xml_text(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        return "\n".join(
            package.read(member).decode("utf-8", "ignore")
            for member in package.namelist()
            if member.endswith(".xml")
        )


def test_report_docx_complete_fixture_preserves_options_and_package_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = _copy_quality_complete_fixture(tmp_path)

    run_vib_report(
        _args(
            plan,
            json=True,
            format="docx",
            theme="satgat-proposal",
            author="팀장",
            title_font_size=31,
            heading_font_size=18,
            body_font_size=14,
            meta_font_size=10,
            heading_font="pretendard",
            body_font="gowun-batang",
            page_numbers=False,
            force=True,
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    text = _package_xml_text(Path(payload["path"]))
    assert "예약 운영 개선 제안 보고서" in text
    assert "파일럿 매장 3곳" in text
    assert "팀장" in text
    assert "Pretendard" in text
    assert "고운바탕" in text
    assert "PAGE" not in text


def test_report_pptx_complete_fixture_preserves_options_and_package_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = _copy_quality_complete_fixture(tmp_path)

    run_vib_report(
        _args(
            plan,
            json=True,
            format="pptx",
            theme="satgat-proposal",
            author="팀장",
            title_font_size=31,
            heading_font_size=18,
            body_font_size=14,
            meta_font_size=10,
            heading_font="pretendard",
            body_font="gowun-batang",
            page_numbers=False,
            force=True,
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    text = _package_xml_text(Path(payload["path"]))
    assert "예약 운영 개선 제안 보고서" in text
    assert "파일럿 매장 3곳" in text
    assert "팀장" in text
    assert "Pretendard" in text
    assert "고운바탕" in text
