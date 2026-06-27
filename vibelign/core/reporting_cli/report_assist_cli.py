# === ANCHOR: REPORT_ASSIST_CLI_START ===
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, cast

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.response_policy import safe_planning_status
from vibelign.core.reporting_cli.report_assist import (
    AssistKind,
    AssistSourceRef,
    AssistSuggestion,
    ReportAssistRequest,
    ReportAssistance,
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_ASSIST_KINDS: tuple[AssistKind, ...] = (
    "draft_text",
    "source_candidate",
    "user_question",
    "risk_candidate",
    "next_action_candidate",
)


@dataclass(frozen=True, slots=True)
class CliAssistProvider:
    provider: str
    root: Path
    runner: cli_adapters.PlanningCliRunner | None = None
    timeout_seconds: int = 90

    def suggest(self, request: ReportAssistRequest) -> ReportAssistance:
        command = cli_adapters.build_cli_command(self.provider, _prompt(request))
        if command is None:
            return _empty_assistance()
        runner = self.runner or cli_adapters.SubprocessPlanningCliRunner()
        result = runner.run(command, cwd=self.root, input_text="", timeout_seconds=self.timeout_seconds)
        if safe_planning_status(result.status, result.stdout) != "ok":
            return _empty_assistance()
        payload = _parse_json_object(result.stdout)
        if payload is None:
            return _empty_assistance()
        return _assistance_from_payload(payload, request["finding_code"])


def _empty_assistance() -> ReportAssistance:
    return {
        "schema_version": "report-assist-v1",
        "status": "ready",
        "suggestions": [],
        "questions": [],
        "applied_suggestion_ids": [],
    }


def _prompt(request: ReportAssistRequest) -> str:
    source_payload = json.dumps(
        {
            "finding_code": request["finding_code"],
            "title": request["title"],
            "outline": request["outline"],
            "chunks": request["chunks"],
        },
        ensure_ascii=False,
    )
    return (
        "한국어 비즈니스 보고서의 부족한 항목을 보완하세요.\n"
        "반드시 원문 chunk에 있는 사실만 사용하고, 원문에 없는 숫자·성과·일정·담당자는 만들지 마세요.\n"
        "리스크 보완은 실행 리스크와 완화 방안을 함께 제안하세요.\n"
        "근거가 부족하면 user_question 제안으로 사용자에게 확인할 질문만 작성하세요.\n"
        "응답은 설명 없이 아래 JSON 객체 하나만 반환하세요.\n"
        '{"schema_version":"report-assist-v1","status":"ready","suggestions":[{"id":"...","finding_code":"...",'
        '"kind":"source_candidate","title":"...","proposed_text":"...","rationale":"...",'
        '"source_refs":[{"chunk_id":"...","heading_path":[],"start_line":1,"end_line":1}],'
        '"requires_user_confirmation":true}],"questions":[],"applied_suggestion_ids":[]}\n\n'
        f"{request['prompt']}\n\n"
        f"입력 JSON:\n{source_payload}"
    )


def _parse_json_object(stdout: str) -> JsonObject | None:
    text = stdout.strip()
    candidates = [text]
    candidates.extend(match.group(1).strip() for match in _JSON_BLOCK_RE.finditer(text))
    if "{" in text and "}" in text:
        candidates.append(text[text.find("{"): text.rfind("}") + 1])
    for candidate in candidates:
        try:
            value = cast(JsonValue, json.loads(candidate))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _assistance_from_payload(payload: JsonObject, finding_code: str) -> ReportAssistance:
    suggestions = _suggestions_from_value(payload.get("suggestions"), finding_code)
    questions = [item for item in suggestions if item["kind"] == "user_question"]
    return {
        "schema_version": "report-assist-v1",
        "status": "needs_user_input" if questions else "ready",
        "suggestions": suggestions,
        "questions": questions,
        "applied_suggestion_ids": [],
    }


def _suggestions_from_value(value: JsonValue | None, finding_code: str) -> list[AssistSuggestion]:
    if not isinstance(value, list):
        return []
    suggestions: list[AssistSuggestion] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        suggestion = _suggestion_from_object(item, finding_code, index)
        if suggestion is not None:
            suggestions.append(suggestion)
    return suggestions[:3]


def _suggestion_from_object(
    item: JsonObject,
    finding_code: str,
    index: int,
) -> AssistSuggestion | None:
    proposed_text = _string_value(item.get("proposed_text")).strip()
    if not proposed_text:
        return None
    kind = _assist_kind(item.get("kind"))
    title = _string_value(item.get("title")).strip() or "보완 제안"
    rationale = _string_value(item.get("rationale")).strip() or "선택한 CLI 모델이 생성한 보완 후보입니다."
    return {
        "id": _string_value(item.get("id")).strip() or f"{finding_code}-cli-{index + 1}",
        "finding_code": finding_code,
        "kind": kind,
        "title": title,
        "proposed_text": proposed_text,
        "rationale": rationale,
        "source_refs": _source_refs_from_value(item.get("source_refs")),
        "requires_user_confirmation": True,
    }


def _assist_kind(value: JsonValue | None) -> AssistKind:
    if isinstance(value, str) and value in _ASSIST_KINDS:
        return value
    return "user_question"


def _source_refs_from_value(value: JsonValue | None) -> list[AssistSourceRef]:
    if not isinstance(value, list):
        return []
    refs: list[AssistSourceRef] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        ref = _source_ref_from_object(item)
        if ref is not None:
            refs.append(ref)
    return refs[:5]


def _source_ref_from_object(item: JsonObject) -> AssistSourceRef | None:
    chunk_id = _string_value(item.get("chunk_id")).strip()
    start_line = _int_value(item.get("start_line"))
    end_line = _int_value(item.get("end_line"))
    if not chunk_id or start_line <= 0 or end_line < start_line:
        return None
    return {
        "chunk_id": chunk_id,
        "heading_path": _string_list_value(item.get("heading_path")),
        "start_line": start_line,
        "end_line": end_line,
    }


def _string_value(value: JsonValue | None) -> str:
    return value if isinstance(value, str) else ""


def _int_value(value: JsonValue | None) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _string_list_value(value: JsonValue | None) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
# === ANCHOR: REPORT_ASSIST_CLI_END ===
