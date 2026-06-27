from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli.emit import emit_report_payload

PLAN = "# 제목\n\n## 한 줄 목표\n성과가 대폭 좋아졌다\n\n## 핵심 기능\n- 예약\n- 알림\n"


def _write_plan(tmp_path: Path) -> Path:
    p = tmp_path / "plan.md"
    p.write_text(PLAN, encoding="utf-8")
    return p


def test_emit_without_polish_has_key_and_base_equals_polished(tmp_path: Path):
    plan = _write_plan(tmp_path)
    payload = emit_report_payload(
        str(plan), "work", date="2026-06-17", polish=False, provider="auto", root=tmp_path
    )
    assert payload["ok"] is True
    assert payload["key"]
    assert payload["base"] == payload["polished"]
    assert payload["guards"] == []
    # '대폭'(한 줄 목표=summary) 이 모호어 경고로 잡힌다.
    assert any(w["term"] == "대폭" for w in payload["vague_warnings"])


def test_emit_without_polish_includes_quality_and_default_assistance(
    tmp_path: Path, monkeypatch
):
    plan = _write_plan(tmp_path)

    def fail_provider_call(*args, **kwargs):
        raise AssertionError("polish provider must not run for default emit-model preflight")

    monkeypatch.setattr(
        "vibelign.core.reporting_cli.emit.polish_report_model_with_guards", fail_provider_call
    )

    payload = emit_report_payload(
        str(plan), "work", date="2026-06-17", polish=False, provider="auto", root=tmp_path
    )

    assert payload["base"] == payload["polished"]
    assert payload["quality"]["schema_version"] == "report-quality-v1"
    assert isinstance(payload["quality"]["findings"], list)
    assert payload["quality"]["findings"]
    assert payload["assistance"] == {
        "schema_version": "report-assist-v1",
        "status": "not_requested",
        "suggestions": [],
        "questions": [],
        "applied_suggestion_ids": [],
    }


def test_emit_with_polish_fills_guards(tmp_path: Path, monkeypatch):
    plan = _write_plan(tmp_path)

    def fake_with_guards(model, **kwargs):
        return model, [{"section": 0, "block": 0, "reason": "number_dropped", "missing": ["50"]}]

    monkeypatch.setattr(
        "vibelign.core.reporting_cli.emit.polish_report_model_with_guards", fake_with_guards
    )
    payload = emit_report_payload(
        str(plan), "work", date="2026-06-17", polish=True, provider="auto", root=tmp_path
    )
    assert payload["guards"] == [{"section": 0, "block": 0, "reason": "number_dropped", "missing": ["50"]}]


def test_emit_doc_type_preserves_arbitrary_sections(tmp_path):
    doc = tmp_path / "free.md"
    doc.write_text("# 자유\n\n## 배경\n설명 문단.\n", encoding="utf-8")

    payload = emit_report_payload(
        str(doc), "doc", date="2026-06-17", polish=False, provider="auto", root=tmp_path
    )

    assert payload["ok"] is True
    assert payload["report_type"] == "doc"
    headings = [s["heading"] for s in payload["base"]["sections"]]
    assert "배경" in headings
