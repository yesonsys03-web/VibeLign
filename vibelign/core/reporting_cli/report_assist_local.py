from __future__ import annotations

from typing import Final, Literal, TypedDict

from vibelign.core.reporting_cli.report_quality import ReportQualityFinding
from vibelign.core.reporting_cli.source_chunks import SourceChunkDict

AssistKind = Literal["draft_text", "source_candidate", "user_question", "risk_candidate", "next_action_candidate"]


class AssistSourceRef(TypedDict):
    chunk_id: str
    heading_path: list[str]
    start_line: int
    end_line: int


class AssistSuggestion(TypedDict):
    id: str
    finding_code: str
    kind: AssistKind
    title: str
    proposed_text: str
    rationale: str
    source_refs: list[AssistSourceRef]
    requires_user_confirmation: bool


_WANTED_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "missing_evidence": ("근거", "지표", "파일럿", "감소", "증가"),
    "missing_risk": ("리스크", "위험", "우려", "혼선"),
    "missing_next_action": ("다음 액션", "후속", "마감", "까지", "배포", "일정"),
    "missing_audience": ("대상", "독자", "사용자", "팀장"),
    "missing_objective": ("목표", "목적", "개선"),
    "missing_decision_or_recommendation": ("결정", "권고", "추천"),
}
_DEFAULT_WORDS: Final[tuple[str, ...]] = ("근거", "다음 액션", "리스크")


def local_suggestions(finding: ReportQualityFinding, chunks: list[SourceChunkDict]) -> list[AssistSuggestion]:
    line = _source_line(finding, chunks)
    if line is not None:
        source_text, source_ref = line
        return [
            {
                "id": f"{finding.code}-{source_ref['chunk_id']}",
                "finding_code": finding.code,
                "kind": _kind_for(finding.code),
                "title": _title_for(finding.code),
                "proposed_text": source_text,
                "rationale": "선택한 문서의 관련 줄에서 가져온 보완 후보입니다.",
                "source_refs": [source_ref],
                "requires_user_confirmation": True,
            }
        ]
    return [*_draft_suggestions(finding), question_for(finding)]


def question_for(finding: ReportQualityFinding) -> AssistSuggestion:
    return {
        "id": f"{finding.code}-question",
        "finding_code": finding.code,
        "kind": "user_question",
        "title": _title_for(finding.code),
        "proposed_text": f"{finding.message} 원문에서 확인되지 않은 사실을 알려주세요.",
        "rationale": "선택한 문서에 충분한 근거가 없어 사용자 확인이 필요합니다.",
        "source_refs": [],
        "requires_user_confirmation": True,
    }


def _draft_suggestions(finding: ReportQualityFinding) -> list[AssistSuggestion]:
    texts = _fallback_texts(finding.code)
    kind = _kind_for(finding.code) if finding.code in {"missing_risk", "missing_next_action"} else "draft_text"
    return [
        {
            "id": f"{finding.code}-draft-{index}",
            "finding_code": finding.code,
            "kind": kind,
            "title": _title_for(finding.code),
            "proposed_text": text,
            "rationale": "원문 근거가 부족해 사용자가 확인해야 하는 보완 후보입니다.",
            "source_refs": [],
            "requires_user_confirmation": True,
        }
        for index, text in enumerate(texts, start=1)
    ]


def _fallback_texts(code: str) -> tuple[str, ...]:
    match code:
        case "missing_audience":
            return ("이 보고서는 서비스 기획자와 운영 담당자가 실행 범위와 우선순위를 빠르게 판단할 수 있도록 작성합니다.",)
        case "missing_objective":
            return ("이번 보고서의 목적은 현재 기획안에서 바로 실행할 수 있는 범위와 보완이 필요한 결정을 명확히 정리하는 것입니다.",)
        case "missing_decision_or_recommendation":
            return ("우선 MVP 범위를 유지하되, 사용자 검증 결과를 확인한 뒤 다음 배포 범위를 결정하는 방향을 권고합니다.",)
        case "missing_risk":
            return (
                "사용자 전환 과정에서 기존 업무 방식과 충돌할 수 있어, 파일럿 그룹을 먼저 운영하고 피드백을 반영합니다.",
                "담당자 확인이 늦어지면 일정이 지연될 수 있으므로, 의사결정 기한과 승인 책임자를 먼저 확정합니다.",
            )
        case "missing_next_action":
            return (
                "다음 액션은 담당자를 지정해 이번 주 안에 사용자 검증 범위와 일정 초안을 확정하는 것입니다.",
                "운영 담당자와 기획 담당자가 변경 요청 처리 기준을 정리하고 다음 회의에서 확정합니다.",
            )
        case _:
            return ()


def _source_line(finding: ReportQualityFinding, chunks: list[SourceChunkDict]) -> tuple[str, AssistSourceRef] | None:
    wanted = _WANTED_WORDS.get(finding.code, _DEFAULT_WORDS)
    for chunk in chunks:
        for offset, line in enumerate(chunk["text"].splitlines()):
            if line.lstrip().startswith("#"):
                continue
            if any(word in line for word in wanted):
                line_number = chunk["start_line"] + offset
                return line.strip().lstrip("-* ").strip(), _ref(chunk, line_number)
    return None


def _ref(chunk: SourceChunkDict, line_number: int) -> AssistSourceRef:
    return {
        "chunk_id": chunk["chunk_id"],
        "heading_path": chunk["heading_path"],
        "start_line": line_number,
        "end_line": line_number,
    }


def _kind_for(code: str) -> AssistKind:
    return {
        "missing_risk": "risk_candidate",
        "missing_next_action": "next_action_candidate",
    }.get(code, "source_candidate")


def _title_for(code: str) -> str:
    return {
        "missing_audience": "대상 독자 확인",
        "missing_objective": "보고 목적 확인",
        "missing_evidence": "근거 보완",
        "missing_decision_or_recommendation": "결정 또는 권고 보완",
        "missing_risk": "리스크 보완",
        "missing_next_action": "다음 액션 보완",
    }.get(code, "보고서 보완")
