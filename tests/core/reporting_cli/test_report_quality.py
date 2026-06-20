from pathlib import Path

from vibelign.core.reporting_cli.models import Block, PlanningData, ReportModel, Section
from vibelign.core.reporting_cli.reader import parse_generic_markdown, parse_plan_markdown
from vibelign.core.reporting_cli.report_quality import analyze_report_quality, quality_to_dict
from vibelign.core.reporting_cli.templates import build_report_model


FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "reporting_cli"
TODAY = "2026-06-20"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _model_from_markdown(text: str, report_type: str) -> tuple[PlanningData, ReportModel]:
    title, sections = parse_generic_markdown(text)
    return (
        parse_plan_markdown(text),
        ReportModel(title=title, report_type=report_type, date=TODAY, sections=sections),
    )


def _finding_codes(model: ReportModel, data: PlanningData, report_type: str) -> set[str]:
    quality = analyze_report_quality(data, model, report_type)
    return {finding.code for finding in quality.findings}


def _assert_finding_contract(model: ReportModel, data: PlanningData, report_type: str) -> None:
    payload = quality_to_dict(analyze_report_quality(data, model, report_type))
    assert set(payload) == {"schema_version", "status", "score", "readiness", "summary", "findings"}
    assert payload["schema_version"] == "report-quality-v1"
    for finding in payload["findings"]:
        assert {"code", "severity", "message", "source", "blocking"} <= set(finding)
        assert finding["code"]
        assert finding["severity"] in {"info", "warn", "block"}
        assert finding["message"]
        assert finding["source"] in {"planning_data", "report_model", "reader", "template", "format"}
        assert isinstance(finding["blocking"], bool)


def test_sparse_fixture_reports_review_warnings_when_business_fields_missing() -> None:
    # Given: a sparse source fixture missing audience, evidence, risk, and next action.
    text = _read_fixture("quality_sparse.md")
    data, model = _model_from_markdown(text, "work")

    # When: deterministic report quality is analyzed.
    quality = analyze_report_quality(data, model, "work")

    # Then: required gaps are non-blocking review warnings with a stable JSON shape.
    codes = {finding.code for finding in quality.findings}
    assert quality.status == "warn"
    assert quality.readiness == "needs_review"
    assert {"missing_audience", "missing_evidence", "missing_risk", "missing_next_action"} <= codes
    assert {finding.code for finding in quality.findings if finding.blocking} == set()
    _assert_finding_contract(model, data, "work")


def test_complete_fixture_is_ready_when_required_business_signals_exist() -> None:
    # Given: a Korean business-report-ready fixture with all required writing signals.
    text = _read_fixture("quality_complete.md")
    data, model = _model_from_markdown(text, "proposal")

    # When: deterministic report quality is analyzed.
    quality = analyze_report_quality(data, model, "proposal")

    # Then: no required missing-field launch code is reported.
    missing_codes = {
        "missing_audience",
        "missing_objective",
        "missing_evidence",
        "missing_decision_or_recommendation",
        "missing_risk",
        "missing_next_action",
    }
    assert quality.status == "ok"
    assert quality.score == 100
    assert quality.readiness == "ready"
    assert missing_codes.isdisjoint({finding.code for finding in quality.findings})
    _assert_finding_contract(model, data, "proposal")


def test_titled_unknown_section_reports_parser_confidence_warning() -> None:
    # Given: a titled markdown document whose body is under an unmapped heading.
    text = "\n".join(
        (
            "# 현장 관찰 메모",
            "",
            "## 현장 메모",
            "예약 담당자가 전화와 메신저를 오가며 같은 변경 요청을 두 번 확인한다.",
        )
    )
    data, model = _model_from_markdown(text, "doc")

    # When: deterministic report quality is analyzed from reader/model surfaces.
    quality = analyze_report_quality(data, model, "doc")

    # Then: the dropped generic body is surfaced as a reader confidence warning.
    parser_findings = [finding for finding in quality.findings if finding.code == "parser_confidence"]
    assert len(parser_findings) == 1
    assert parser_findings[0].source == "reader"
    assert parser_findings[0].blocking is False


def test_long_fixture_scans_middle_sections_when_signals_are_not_at_edges() -> None:
    # Given: a long fixture with evidence, risk, and next-action cues in middle sections.
    text = _read_fixture("quality_long_2000.md")
    lines = text.splitlines()
    data, model = _model_from_markdown(text, "work")

    # When: deterministic report quality is analyzed.
    codes = _finding_codes(model, data, "work")

    # Then: middle-of-file signals are detected without head/tail truncation.
    assert len(lines) >= 2000
    assert "중간근거-품질" not in "\n".join(lines[:200])
    assert "중간근거-품질" not in "\n".join(lines[-200:])
    assert "missing_evidence" not in codes
    assert "missing_risk" not in codes
    assert "missing_next_action" not in codes


def test_empty_content_is_only_default_blocking_category_for_malformed_models() -> None:
    # Given: malformed report models with no usable report content.
    data = PlanningData()
    empty_model = ReportModel(title="", report_type="work", date=TODAY)
    odd_model = ReportModel(
        title="Odd",
        report_type="work",
        date=TODAY,
        sections=[Section(heading="Odd", blocks=[Block(kind="odd")])],
    )

    # When: deterministic report quality is analyzed.
    empty_quality = analyze_report_quality(data, empty_model, "work")
    odd_quality = analyze_report_quality(data, odd_model, "work")

    # Then: only empty_content blocks by default; other gaps remain warnings.
    assert {finding.code for finding in empty_quality.findings if finding.blocking} == {"empty_content"}
    assert {finding.code for finding in odd_quality.findings if finding.blocking} == {"empty_content"}
    assert empty_quality.status == "block"
    assert odd_quality.readiness == "blocked"


def test_analyzer_does_not_mutate_report_model() -> None:
    # Given: a direct in-memory model whose sections should stay unchanged.
    data = PlanningData(idea="보고 목표", target_users="운영팀", decisions=["진행 권고"])
    model = ReportModel(
        title="불변성 확인",
        report_type="work",
        date=TODAY,
        sections=[
            Section(
                heading="근거와 실행",
                blocks=[
                    Block(kind="bullets", items=["근거: 처리 시간 12분 단축", "리스크: 교육 누락", "다음 액션: 7월 5일까지 배포"]),
                ],
            )
        ],
    )
    before = list(model.sections)

    # When: quality is analyzed and serialized.
    quality_to_dict(analyze_report_quality(data, model, "work"))

    # Then: the original ReportModel remains untouched.
    assert model.sections == before


def test_fixture_quality_is_stable_across_supported_report_types() -> None:
    # Given: Todo 1 fixtures reused through the backend template surface.
    sparse = parse_plan_markdown(_read_fixture("quality_sparse.md"))
    complete = parse_plan_markdown(_read_fixture("quality_complete.md"))

    # When: each template-backed report type is analyzed.
    sparse_by_type = {
        report_type: analyze_report_quality(
            sparse,
            build_report_model(sparse, report_type, date=TODAY),
            report_type,
        )
        for report_type in ("work", "proposal", "result")
    }
    complete_by_type = {
        report_type: analyze_report_quality(
            complete,
            build_report_model(complete, report_type, date=TODAY),
            report_type,
        )
        for report_type in ("work", "proposal", "result")
    }

    # Then: sparse stays review-needed and complete stays ready for every backend report type.
    assert {quality.status for quality in sparse_by_type.values()} == {"warn"}
    assert {quality.readiness for quality in complete_by_type.values()} == {"ready"}


def test_doc_report_type_uses_generic_markdown_without_format_risk() -> None:
    # Given: a complete generic markdown document rendered through the doc backend path.
    text = _read_fixture("quality_complete.md")
    data, model = _model_from_markdown(text, "doc")

    # When: doc quality is analyzed.
    codes = _finding_codes(model, data, "doc")

    # Then: doc is accepted as a first-class report type.
    assert "format_risk" not in codes
    assert "empty_content" not in codes


def test_bullet_scanning_detects_evidence_action_and_risk_cues() -> None:
    # Given: all business signals appear inside bullet blocks, not paragraphs.
    data = PlanningData(
        title="불릿 보고",
        idea="운영 기준을 개선한다.",
        target_users="운영팀장",
        decisions=["예약 대기열을 우선 도입한다."],
    )
    model = ReportModel(
        title="불릿 보고",
        report_type="work",
        date=TODAY,
        sections=[
            Section(
                heading="검토",
                blocks=[
                    Block(
                        kind="bullets",
                        items=[
                            "근거: 파일럿 3곳에서 처리 시간이 18% 감소했다.",
                            "리스크: 교육 누락 시 현장 혼선이 생긴다.",
                            "다음 액션: 운영팀장이 2026-07-05까지 교육안을 배포한다.",
                        ],
                    )
                ],
            )
        ],
    )

    # When: quality scans the report model.
    codes = _finding_codes(model, data, "work")

    # Then: bullet-only cues satisfy evidence, risk, and next-action checks.
    assert "missing_evidence" not in codes
    assert "missing_risk" not in codes
    assert "missing_next_action" not in codes
