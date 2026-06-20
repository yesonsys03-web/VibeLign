# === ANCHOR: REPORT_QUALITY_START ===
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal, TypedDict

from vibelign.core.reporting_cli.models import Block, PlanningData, ReportModel, Section

REPORT_QUALITY_SCHEMA_VERSION: Final = "report-quality-v1"

ReportQualityStatus = Literal["ok", "warn", "block"]
ReportQualitySeverity = Literal["info", "warn", "block"]
ReportQualityReadiness = Literal["ready", "needs_review", "blocked"]
ReportQualitySource = Literal["planning_data", "report_model", "reader", "template", "format"]

class ReportQualityFindingDict(TypedDict, total=False):
    code: str
    severity: ReportQualitySeverity
    message: str
    source: ReportQualitySource
    blocking: bool
    section: int
    block: int
    suggestion: str


class ReportQualityDict(TypedDict):
    schema_version: str
    status: ReportQualityStatus
    score: int
    readiness: ReportQualityReadiness
    summary: str
    findings: list[ReportQualityFindingDict]


@dataclass(frozen=True)
class ReportQualityFinding:
    code: str
    severity: ReportQualitySeverity
    message: str
    source: ReportQualitySource
    blocking: bool
    section: int | None = None
    block: int | None = None
    suggestion: str | None = None


@dataclass(frozen=True)
class ReportQuality:
    schema_version: str
    status: ReportQualityStatus
    score: int
    readiness: ReportQualityReadiness
    summary: str
    findings: tuple[ReportQualityFinding, ...]


@dataclass(frozen=True)
class _QualityRule:
    code: str
    message: str
    source: ReportQualitySource
    suggestion: str
    weight: int
    severity: ReportQualitySeverity = "warn"
    blocking: bool = False


@dataclass(frozen=True)
class _QualityText:
    report_type: str
    model_text: str
    all_text: str


_KNOWN_REPORT_TYPES: Final[frozenset[str]] = frozenset({"work", "proposal", "result", "doc"})
_METRIC_RE: Final[re.Pattern[str]] = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|퍼센트|건|명|분|시간|일|원|회|배|점|개|주)"
)
_RISK_WORDS: Final[tuple[str, ...]] = ("리스크", "위험", "우려", "혼선", "누락", "지연", "대응", "완화")
_ACTION_WORDS: Final[tuple[str, ...]] = ("다음 액션", "후속", "마감", "까지", "배포", "실행", "일정")
_EVIDENCE_WORDS: Final[tuple[str, ...]] = ("근거", "지표", "데이터", "측정", "파일럿", "감소", "증가", "평균", "분석")
_AUDIENCE_WORDS: Final[tuple[str, ...]] = ("대상", "독자", "사용자", "고객", "수신자", "팀장")
_OBJECTIVE_WORDS: Final[tuple[str, ...]] = ("목표", "목적", "하려고", "개선", "달성", "줄이고")
_DECISION_WORDS: Final[tuple[str, ...]] = ("결정", "권고", "추천", "제안", "도입", "출시", "우선")
_MISSING_RULES: Final[tuple[_QualityRule, ...]] = (
    _QualityRule("missing_audience", "보고서 독자나 대상 사용자가 드러나지 않습니다.", "planning_data", "대상 독자와 사용자를 한 문장으로 추가하세요.", 12),
    _QualityRule("missing_objective", "보고서 목적이나 달성하려는 목표가 부족합니다.", "planning_data", "이번 보고서가 결정하게 할 목표를 명시하세요.", 12),
    _QualityRule("missing_evidence", "근거, 지표, 수치, 관찰 데이터가 부족합니다.", "report_model", "판단 근거가 되는 수치나 관찰 내용을 추가하세요.", 14),
    _QualityRule("missing_decision_or_recommendation", "결정 사항이나 권고가 드러나지 않습니다.", "planning_data", "실행할 결정 또는 추천 방향을 명확히 쓰세요.", 12),
    _QualityRule("missing_risk", "리스크와 대응 관점이 부족합니다.", "report_model", "실행 리스크와 완화 방안을 함께 추가하세요.", 12),
    _QualityRule("missing_next_action", "다음 액션, 담당자, 일정이 부족합니다.", "report_model", "담당자와 기한이 있는 후속 조치를 추가하세요.", 12),
)
_EMPTY_CONTENT_RULE: Final = _QualityRule(
    "empty_content",
    "선택한 보고서 종류에서 생성된 본문 섹션이 없습니다.",
    "report_model",
    "기획안 내용을 채우거나 문서 그대로 보고서로 전환하세요.",
    100,
    "block",
    True,
)
_FORMAT_RISK_RULE: Final = _QualityRule(
    "format_risk",
    "선택한 보고서 종류와 생성된 모델 형식이 일치하지 않거나 알 수 없습니다.",
    "format",
    "보고서 종류를 다시 선택한 뒤 생성하세요.",
    4,
)
_PARSER_CONFIDENCE_RULE: Final = _QualityRule(
    "parser_confidence",
    "원본 섹션 일부가 구조화된 기획 필드로 매핑되지 않았을 수 있습니다.",
    "reader",
    "문서 그대로 보고서 또는 표준 기획안 headings 사용을 검토하세요.",
    4,
)
_UNRESOLVED_QUESTIONS_RULE: Final = _QualityRule(
    "unresolved_questions",
    "아직 결정되지 않은 질문이 남아 있습니다.",
    "planning_data",
    "미결 질문을 결정 사항 또는 다음 액션으로 정리하세요.",
    6,
)
_MISSING_AUDIENCE, _MISSING_OBJECTIVE, _MISSING_EVIDENCE, _MISSING_DECISION, _MISSING_RISK, _MISSING_NEXT_ACTION = _MISSING_RULES
_WEIGHT_BY_CODE: Final[dict[str, int]] = {
    rule.code: rule.weight
    for rule in (*_MISSING_RULES, _FORMAT_RISK_RULE, _PARSER_CONFIDENCE_RULE, _UNRESOLVED_QUESTIONS_RULE)
}


def analyze_report_quality(data: PlanningData, model: ReportModel, report_type: str) -> ReportQuality:
    model_text = _model_text(model)
    quality_text = _QualityText(report_type, model_text, "\n".join((_planning_text(data), model.title, model_text)))
    findings = _base_findings(data, model, quality_text)
    score = _score(findings)
    status = _status(findings)
    readiness = _readiness(status)
    return ReportQuality(
        schema_version=REPORT_QUALITY_SCHEMA_VERSION,
        status=status,
        score=score,
        readiness=readiness,
        summary=_summary(status, score, findings),
        findings=tuple(findings),
    )


def quality_to_dict(quality: ReportQuality) -> ReportQualityDict:
    return {
        "schema_version": quality.schema_version,
        "status": quality.status,
        "score": quality.score,
        "readiness": quality.readiness,
        "summary": quality.summary,
        "findings": [_finding_to_dict(finding) for finding in quality.findings],
    }


def _base_findings(data: PlanningData, model: ReportModel, quality_text: _QualityText) -> list[ReportQualityFinding]:
    findings: list[ReportQualityFinding] = []
    if not _model_body_text(model).strip():
        findings.append(_finding_from_rule(_EMPTY_CONTENT_RULE))
    if quality_text.report_type not in _KNOWN_REPORT_TYPES or model.report_type != quality_text.report_type:
        findings.append(_finding_from_rule(_FORMAT_RISK_RULE))
    if _parser_confidence_is_low(data, model):
        findings.append(_finding_from_rule(_PARSER_CONFIDENCE_RULE))
    findings.extend(_finding_from_rule(rule) for rule in _missing_rules(data, quality_text.all_text, quality_text.model_text))
    if data.open_questions or "?" in quality_text.model_text or "？" in quality_text.model_text:
        findings.append(_finding_from_rule(_UNRESOLVED_QUESTIONS_RULE))
    return findings


def _missing_rules(data: PlanningData, all_text: str, model_text: str) -> tuple[_QualityRule, ...]:
    checks = (
        (not data.target_users and not _contains_any(all_text, _AUDIENCE_WORDS), _MISSING_AUDIENCE),
        (not data.idea and not _contains_any(all_text, _OBJECTIVE_WORDS), _MISSING_OBJECTIVE),
        (not _has_evidence(model_text), _MISSING_EVIDENCE),
        (not data.decisions and not _contains_any(all_text, _DECISION_WORDS), _MISSING_DECISION),
        (not _contains_any(model_text, _RISK_WORDS), _MISSING_RISK),
        (not _contains_any(model_text, _ACTION_WORDS), _MISSING_NEXT_ACTION),
    )
    return tuple(rule for missing, rule in checks if missing)


def _finding_from_rule(rule: _QualityRule) -> ReportQualityFinding:
    return ReportQualityFinding(
        code=rule.code,
        severity=rule.severity,
        message=rule.message,
        source=rule.source,
        blocking=rule.blocking,
        suggestion=rule.suggestion,
    )


def _finding_to_dict(finding: ReportQualityFinding) -> ReportQualityFindingDict:
    payload: ReportQualityFindingDict = {
        "code": finding.code,
        "severity": finding.severity,
        "message": finding.message,
        "source": finding.source,
        "blocking": finding.blocking,
    }
    if finding.section is not None:
        payload["section"] = finding.section
    if finding.block is not None:
        payload["block"] = finding.block
    if finding.suggestion is not None:
        payload["suggestion"] = finding.suggestion
    return payload


def _score(findings: list[ReportQualityFinding]) -> int:
    if any(finding.code == "empty_content" and finding.blocking for finding in findings):
        return 0
    penalty = 0
    for finding in findings:
        penalty += _WEIGHT_BY_CODE.get(finding.code, 0)
    return max(0, 100 - penalty)


def _status(findings: list[ReportQualityFinding]) -> ReportQualityStatus:
    if any(finding.blocking for finding in findings):
        return "block"
    return "warn" if findings else "ok"


def _readiness(status: ReportQualityStatus) -> ReportQualityReadiness:
    return {"block": "blocked", "warn": "needs_review", "ok": "ready"}[status]


def _summary(
    status: ReportQualityStatus,
    score: int,
    findings: list[ReportQualityFinding],
) -> str:
    if status == "ok":
        return f"보고서 품질 점검을 통과했습니다. 점수 {score}점."
    if status == "block":
        return f"본문이 비어 있어 생성 전 보완이 필요합니다. 점수 {score}점."
    return f"{len(findings)}개 품질 경고를 검토하세요. 점수 {score}점."


def _parser_confidence_is_low(data: PlanningData, model: ReportModel) -> bool:
    return not _planning_signal_text(data).strip() and bool(_model_body_text(model).strip())


def _model_text(model: ReportModel) -> str:
    parts: list[str] = []
    for section in model.sections:
        parts.extend(_section_texts(section))
    return "\n".join(parts)


def _model_body_text(model: ReportModel) -> str:
    parts: list[str] = []
    for section in model.sections:
        for block in section.blocks:
            parts.append(_block_text(block))
    return "\n".join(part for part in parts if part.strip())


def _section_texts(section: Section) -> tuple[str, ...]:
    parts = [section.heading]
    for block in section.blocks:
        parts.append(_block_text(block))
    return tuple(part for part in parts if part.strip())


def _block_text(block: Block) -> str:
    return "\n".join((block.text, *block.items)).strip()


def _planning_text(data: PlanningData) -> str:
    return "\n".join((data.title, _planning_signal_text(data)))


def _planning_signal_text(data: PlanningData) -> str:
    return "\n".join(
        (
            data.idea,
            data.target_users,
            data.problem,
            "\n".join(data.features),
            "\n".join(data.flows),
            "\n".join(data.decisions),
            "\n".join(data.exclusions),
            "\n".join(data.open_questions),
            data.context_notes,
        )
    )


def _has_evidence(text: str) -> bool:
    return bool(_METRIC_RE.search(text)) or _contains_any(text, _EVIDENCE_WORDS)


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)
# === ANCHOR: REPORT_QUALITY_END ===
