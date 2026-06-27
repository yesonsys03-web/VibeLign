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
    )
    base.update(over)
    return Namespace(**base)


def test_report_polish_off_by_default_no_provider_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    called = {"n": 0}
    import vibelign.commands.vib_report_cmd as cmd
    monkeypatch.setattr(cmd, "polish_report_model", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or a[0])
    run_vib_report(_args(plan, json=True))
    assert called["n"] == 0


def test_report_polish_on_calls_polish(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    seen = {}
    import vibelign.commands.vib_report_cmd as cmd

    def fake_polish(model, *, provider, root, **k):
        seen["provider"] = provider
        return model

    monkeypatch.setattr(cmd, "polish_report_model", fake_polish)
    run_vib_report(_args(plan, json=True, polish=True, cli="auto"))
    assert seen.get("provider") == "auto"


def test_report_polish_uses_cache_on_second_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    calls = {"n": 0}
    import vibelign.commands.vib_report_cmd as cmd

    def counting(model, **k):
        calls["n"] += 1
        return model

    monkeypatch.setattr(cmd, "polish_report_model", counting)
    run_vib_report(_args(plan, json=True, polish=True, cli="auto"))
    run_vib_report(_args(plan, json=True, polish=True, cli="auto"))
    assert calls["n"] == 1


def test_emit_model_prints_base_polished_and_key(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, emit_model=True))
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
    assert "base" in out and "polished" in out and out["key"]
    assert out["base"]["report_type"] == "work"
    assert out["base"] == out["polished"]
    assert isinstance(out["quality"]["findings"], list)
    assert out["assistance"]["status"] == "not_requested"
    assert out["assistance"]["suggestions"] == []
    assert out["assistance"]["questions"] == []
    assert out["assistance"]["applied_suggestion_ids"] == []


def test_render_decisions_writes_file(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    monkeypatch.setattr(
        "vibelign.core.reporting_cli.emit.polish_report_model_with_guards",
        lambda m, **k: (m, []),
    )
    run_vib_report(_args(plan, json=True, emit_model=True, polish=True))
    key = json.loads(capsys.readouterr().out.strip())["key"]
    run_vib_report(_args(plan, json=True, reject_blocks="[[0,0]]", polish_key=key))
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
    assert Path(out["path"]).exists()


def test_render_decisions_payload_file_malformed_schema_reports_json_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    run_vib_report(_args(plan, json=True, emit_model=True))
    payload = json.loads(capsys.readouterr().out.strip())
    payload["base"]["sections"][0]["blocks"][0]["items"] = 1
    payload_path = tmp_path / "render-payload-malformed.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("VIBELIGN_REPORT_RENDER_PAYLOAD_PATH", str(payload_path))

    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True, reject_blocks="[]", polish_key=payload["key"]))

    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is False
    assert "render payload 형식이 잘못됐어요" in out["error"]


def test_render_decisions_payload_file_non_string_block_text_reports_json_error_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")

    run_vib_report(_args(plan, json=True, emit_model=True))
    payload = json.loads(capsys.readouterr().out.strip())
    payload["base"]["sections"][0]["blocks"][0]["text"] = 1
    payload_path = tmp_path / "render-payload-malformed-block-text.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("VIBELIGN_REPORT_RENDER_PAYLOAD_PATH", str(payload_path))

    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True, reject_blocks="[]", polish_key=payload["key"]))

    captured = capsys.readouterr()
    out = json.loads(captured.out.strip())
    assert out["ok"] is False
    assert "render payload 형식이 잘못됐어요" in out["error"]
    assert "text" in out["error"]
    assert captured.err == ""


def test_render_decisions_cache_miss_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True, reject_blocks="[[0,0]]", polish_key="deadbeef"))
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is False


def test_theme_threads_to_html(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, theme="minimal"))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert "text-transform:uppercase" in Path(out["path"]).read_text(encoding="utf-8")


def test_generated_theme_threads_to_html(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, theme="letter-wine-balanced"))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    html = Path(out["path"]).read_text(encoding="utf-8")
    assert "#8A2545" in html
    assert "text-align:center" in html


def test_font_sizes_thread_to_html(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, title_font_size=32, heading_font_size=19, body_font_size=15, meta_font_size=11))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    html = Path(out["path"]).read_text(encoding="utf-8")
    assert "h1 { font-size:32px; }" in html
    assert "h2 { font-size:19px; }" in html
    assert "body { font-size:15px; }" in html
    assert "p.meta { font-size:11px; }" in html


def test_invalid_font_size_reports_error_json(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True, title_font_size=7))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "8~72" in out["error"]


def test_fonts_thread_to_html(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, heading_font="pretendard", body_font=None))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    html = Path(out["path"]).read_text(encoding="utf-8")
    assert "@font-face" in html
    assert '"Pretendard"' in html


def test_invalid_font_reports_error_json(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True, heading_font="not-a-font"))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False


def test_unknown_theme_reports_short_error_json(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    with pytest.raises(SystemExit):
        run_vib_report(_args(plan, json=True, theme="not-a-theme"))
    out = json.loads(capsys.readouterr().out)
    assert out == {"ok": False, "error": "알 수 없는 디자인 테마예요: not-a-theme"}


def test_author_threads_to_html(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    run_vib_report(_args(plan, json=True, author="홍길동"))
    out = json.loads(capsys.readouterr().out)
    assert "작성자: 홍길동" in Path(out["path"]).read_text(encoding="utf-8")
