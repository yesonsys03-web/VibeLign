import pytest

from vibelign.core.reporting_cli.models import PlanningData
from vibelign.core.reporting_cli.templates import REPORT_TEMPLATES, build_report_model


def _sample() -> PlanningData:
    return PlanningData(
        title="예약 앱",
        idea="미용실 예약 앱",
        target_users="미용실 사장님",
        features=["예약 캘린더", "알림 문자"],
        flows=["손님 선택", "사장 확정"],
        decisions=["MVP 는 캘린더만"],
        open_questions=["노쇼 정책?"],
    )


def test_all_three_types_registered():
    assert set(REPORT_TEMPLATES) == {"work", "proposal", "result"}


def test_build_uses_title_and_date():
    model = build_report_model(
        _sample(),
        "work",
        date="2026-06-15",
        source_plan_path="plans/예약-앱.md",
    )
    assert model.report_type == "work"
    assert model.title == "예약 앱"
    assert model.date == "2026-06-15"
    assert model.source_plan_path == "plans/예약-앱.md"


def test_build_skips_empty_sources():
    data = PlanningData(idea="아이디어만 있음")
    model = build_report_model(data, "work", date="2026-06-15")
    headings = [s.heading for s in model.sections]
    # features/flows 가 비었으므로 그 섹션은 빠진다
    assert "개요" in headings
    assert "핵심 내용" not in headings


def test_build_bullets_block_for_list_source():
    model = build_report_model(_sample(), "work", date="2026-06-15")
    section = next(s for s in model.sections if s.heading == "핵심 내용")
    assert section.blocks[0].kind == "bullets"
    assert section.blocks[0].items == ["예약 캘린더", "알림 문자"]


def test_build_unknown_type_raises():
    with pytest.raises(ValueError):
        build_report_model(_sample(), "nope", date="2026-06-15")
