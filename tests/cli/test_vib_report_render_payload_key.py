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


def test_render_decisions_payload_file_matching_key_writes_draft_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text(PLAN_MD, encoding="utf-8")
    monkeypatch.setattr(
        "vibelign.core.reporting_cli.emit.polish_report_model_with_guards",
        lambda m, **k: (m, []),
    )

    run_vib_report(_args(plan, json=True, emit_model=True, polish=True))
    payload = json.loads(capsys.readouterr().out.strip())
    draft_section = {
        "heading": "사용자 확인 보완 초안",
        "blocks": [
            {
                "kind": "paragraph",
                "text": "최종 저장 검증 문장: 이탈률 18% 감소",
                "items": [],
            }
        ],
    }
    payload["base"]["sections"].append(draft_section)
    payload["polished"]["sections"].append(draft_section)
    payload_path = tmp_path / "render-payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("VIBELIGN_REPORT_RENDER_PAYLOAD_PATH", str(payload_path))

    run_vib_report(_args(plan, json=True, reject_blocks="[]", polish_key=payload["key"]))

    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True
    html = Path(out["path"]).read_text(encoding="utf-8")
    assert "사용자 확인 보완 초안" in html
    assert "최종 저장 검증 문장: 이탈률 18% 감소" in html


@pytest.mark.parametrize("polish_key", [None, "stale-polish-key"])
def test_render_decisions_payload_file_rejects_missing_or_mismatched_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    polish_key: str | None,
):
    monkeypatch.chdir(tmp_path)
    alpha_plan = tmp_path / "alpha.md"
    beta_plan = tmp_path / "beta.md"
    alpha_plan.write_text(PLAN_MD, encoding="utf-8")
    beta_plan.write_text("# 결제 앱\n\n## 한 줄 목표\n구독 결제 앱.\n", encoding="utf-8")

    run_vib_report(_args(alpha_plan, json=True, emit_model=True))
    payload = json.loads(capsys.readouterr().out.strip())
    stale_marker = "알파 플랜 전용 문장: 이 문장이 베타 보고서에 있으면 안 됨"
    stale_section = {"heading": "알파 전용 섹션", "blocks": [{"kind": "paragraph", "text": stale_marker, "items": []}]}
    payload["base"]["sections"].append(stale_section)
    payload["polished"]["sections"].append(stale_section)
    payload_path = tmp_path / "stale-render-payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("VIBELIGN_REPORT_RENDER_PAYLOAD_PATH", str(payload_path))

    with pytest.raises(SystemExit):
        run_vib_report(_args(beta_plan, json=True, reject_blocks="[]", polish_key=polish_key))

    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is False
    assert all(stale_marker not in path.read_text(encoding="utf-8") for path in tmp_path.glob("*.html"))
