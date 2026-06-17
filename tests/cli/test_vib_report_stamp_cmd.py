import json
from argparse import Namespace


def _two_page_pdf(p):
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(p))
    c.drawString(72, 720, "a")
    c.showPage()
    c.drawString(72, 720, "b")
    c.showPage()
    c.save()


def test_stamp_cmd_json(tmp_path, capsys):
    from vibelign.commands.vib_report_stamp_cmd import run_vib_report_stamp

    pdf = tmp_path / "r.pdf"
    _two_page_pdf(pdf)
    run_vib_report_stamp(Namespace(pdf=str(pdf), json=True))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True and out["pages"] == 2 and out["path"] == str(pdf)


def test_stamp_cmd_missing_file(tmp_path, capsys):
    import pytest

    from vibelign.commands.vib_report_stamp_cmd import run_vib_report_stamp

    with pytest.raises(SystemExit):
        run_vib_report_stamp(Namespace(pdf=str(tmp_path / "nope.pdf"), json=True))
    assert json.loads(capsys.readouterr().out)["ok"] is False
