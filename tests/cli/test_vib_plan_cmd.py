import json
from argparse import Namespace
from pathlib import Path

import pytest

from vibelign.cli.vib_cli import build_parser
from vibelign.commands.vib_plan_cmd import run_vib_plan


def test_vib_plan_parser_registers_template_only() -> None:
    parser = build_parser()
    args = parser.parse_args(["plan", "예약 앱", "--template-only", "--json"])
    assert args.template_only is True
    assert args.json is True


def test_vib_plan_template_only_json_outputs_result(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    run_vib_plan(Namespace(idea=["예약 앱"], template_only=True, output=None, force=False, language="auto", json=True))

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["output_path"] == "plans/예약-앱.md"
    assert payload["fallback_reason"] == "template_only"
    assert (tmp_path / payload["output_path"]).exists()


def test_vib_plan_without_template_only_is_reserved_for_later() -> None:
    with pytest.raises(SystemExit):
        run_vib_plan(Namespace(idea=["예약 앱"], template_only=False, output=None, force=False, language="auto", json=False))
