import json
from pathlib import Path

import pytest

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.reporting_cli.reader import parse_plan_markdown
from vibelign.core.reporting_cli.report_assist import (
    AssistProvider,
    ReportAssistRequest,
    ReportAssistance,
    generate_report_assistance,
)
from vibelign.core.reporting_cli.report_assist_cli import CliAssistProvider
from vibelign.core.reporting_cli.report_quality import analyze_report_quality
from vibelign.core.reporting_cli.source_chunks import (
    build_source_index,
    retrieve_relevant_chunks,
)
from vibelign.core.reporting_cli.templates import build_report_model


FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "reporting_cli"
TODAY = "2026-06-20"


class UnsupportedEvidenceProvider:
    def suggest(self, request: ReportAssistRequest) -> ReportAssistance:
        if request["finding_code"] != "missing_evidence":
            return {
                "schema_version": "report-assist-v1",
                "status": "ready",
                "suggestions": [],
                "questions": [],
                "applied_suggestion_ids": [],
            }
        return {
            "schema_version": "report-assist-v1",
            "status": "ready",
            "suggestions": [
                {
                    "id": "fake-unsupported-evidence",
                    "finding_code": "missing_evidence",
                    "kind": "source_candidate",
                    "title": "Unsupported metric",
                    "proposed_text": "근거: 전환율이 92% 개선되었습니다.",
                    "rationale": "provider output without source support",
                    "source_refs": [],
                    "requires_user_confirmation": False,
                }
            ],
            "questions": [],
            "applied_suggestion_ids": ["fake-unsupported-evidence"],
        }


class EchoPromptProvider:
    def __init__(self) -> None:
        self.prompt_line_counts: list[int] = []

    def suggest(self, request: ReportAssistRequest) -> ReportAssistance:
        self.prompt_line_counts.append(len(request["prompt"].splitlines()))
        return {
            "schema_version": "report-assist-v1",
            "status": "ready",
            "suggestions": [],
            "questions": [],
            "applied_suggestion_ids": [],
        }


class StubCliRunner:
    stdout: str
    commands: list[list[str]]
    cwd: Path | None

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.commands = []
        self.cwd = None

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    ) -> cli_adapters.PlanningCliResult:
        _ = (input_text, timeout_seconds)
        self.commands.append(command)
        self.cwd = cwd
        return cli_adapters.PlanningCliResult(
            status="ok",
            stdout=self.stdout,
            stderr="",
            exit_code=0,
            duration_ms=1,
        )


class RecordingProvider:
    """Records one suggest() call per finding and returns a guard-passing draft suggestion."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def suggest(self, request: ReportAssistRequest) -> ReportAssistance:
        code = request["finding_code"]
        self.calls.append(code)
        return {
            "schema_version": "report-assist-v1",
            "status": "ready",
            "suggestions": [
                {
                    "id": f"s-{code}",
                    "finding_code": code,
                    "kind": "draft_text",
                    "title": "보완",
                    "proposed_text": "보완 문단",
                    "rationale": "근거",
                    "source_refs": [],
                    "requires_user_confirmation": True,
                }
            ],
            "questions": [],
            "applied_suggestion_ids": [],
        }


def test_assistance_reports_progress_and_calls_provider_once_per_missing_finding() -> None:
    text = _fixture("quality_sparse.md")
    provider = RecordingProvider()
    progress: list[tuple[int, int]] = []

    payload = generate_report_assistance(
        text, "proposal", date=TODAY, provider=provider, on_progress=lambda done, total: progress.append((done, total))
    )

    total = len(provider.calls)
    assert total >= 2, "sparse input should yield multiple missing findings"
    # progress is emitted from 0..total against a stable total, monotonically.
    assert progress, "on_progress must be called"
    assert progress[0] == (0, total)
    assert progress[-1] == (total, total)
    assert [d for d, _ in progress] == sorted(d for d, _ in progress)
    assert all(t == total for _, t in progress)
    # Every missing finding still receives a suggestion (order preserved by index assembly).
    out_codes = [s["finding_code"] for s in payload["suggestions"]]
    for code in provider.calls:
        assert code in out_codes


def _fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_sparse_input_yields_recommendations_and_user_questions_without_provider_call() -> None:
    # Given: sparse source lacks evidence, risk, and next-action facts.
    text = _fixture("quality_sparse.md")

    # When: assistance is generated from deterministic findings.
    payload = generate_report_assistance(text, "proposal", date=TODAY)

    # Then: it offers selectable recommendations while still asking for missing facts.
    questions = [item for item in payload["suggestions"] if item["kind"] == "user_question"]
    recommendation_kinds = {
        item["kind"]
        for item in payload["suggestions"]
        if item["kind"] != "user_question"
    }
    assert payload["status"] == "needs_user_input"
    assert questions
    assert {"draft_text", "risk_candidate"} <= recommendation_kinds
    assert payload["questions"] == questions
    assert payload["applied_suggestion_ids"] == []


def test_complete_input_does_not_fabricate_unsupported_evidence() -> None:
    # Given: complete source has no missing evidence finding.
    text = _fixture("quality_complete.md")

    # When: assistance is requested.
    payload = generate_report_assistance(text, "proposal", date=TODAY)

    # Then: no unsupported missing-evidence suggestion is invented.
    assert payload["status"] == "ready"
    assert [
        item
        for item in payload["suggestions"]
        if item["finding_code"] == "missing_evidence"
    ] == []


def test_long_source_builds_multiple_chunks_with_stable_line_ranges() -> None:
    # Given: a 2,000-line source fixture.
    text = _fixture("quality_long_2000.md")

    # When: the source index is built.
    index = build_source_index(text)

    # Then: long mode creates ordered chunks with bounded, stable line ranges.
    assert index["is_long_source"] is True
    assert len(index["chunks"]) > 5
    assert index["chunks"][0]["start_line"] == 1
    assert all(chunk["start_line"] <= chunk["end_line"] for chunk in index["chunks"])
    assert all(len(chunk["text"].splitlines()) <= 220 for chunk in index["chunks"])


def test_retrieved_chunks_include_middle_signal_section() -> None:
    # Given: quality findings are produced from the template-backed long source.
    text = _fixture("quality_long_2000.md")
    data = parse_plan_markdown(text)
    model = build_report_model(data, "work", date=TODAY)
    quality = analyze_report_quality(data, model, "work")
    missing_evidence = next(finding for finding in quality.findings if finding.code == "missing_evidence")
    index = build_source_index(text)

    # When: relevant chunks are retrieved for the missing evidence finding.
    chunks = retrieve_relevant_chunks(index, missing_evidence)

    # Then: retrieval is capped and includes middle-of-file evidence, risk, and action signals.
    assert len(chunks) <= 5
    assert any(chunk["start_line"] <= 1100 and chunk["end_line"] >= 900 for chunk in chunks)
    retrieved_signals = {signal for chunk in chunks for signal in chunk["signals"]}
    assert {"evidence", "number", "risk", "action"} <= retrieved_signals


def test_fake_provider_output_is_guarded_before_serialization() -> None:
    # Given: a fake provider returns unsupported evidence and auto-applied IDs.
    text = _fixture("quality_sparse.md")
    provider: AssistProvider = UnsupportedEvidenceProvider()

    # When: assistance is generated.
    payload = generate_report_assistance(text, "proposal", date=TODAY, provider=provider)

    # Then: unsupported evidence is downgraded to a user question and never applied.
    item = next(item for item in payload["suggestions"] if item["finding_code"] == "missing_evidence")
    assert item["kind"] == "user_question"
    assert item["requires_user_confirmation"] is True
    assert item["source_refs"] == []
    assert item in payload["questions"]
    assert payload["applied_suggestion_ids"] == []


def test_long_source_provider_prompt_uses_retrieved_chunks_not_full_file() -> None:
    # Given: a fake provider records prompt sizes.
    text = _fixture("quality_long_2000.md")
    provider = EchoPromptProvider()

    # When: assistance is generated for long source.
    payload = generate_report_assistance(text, "work", date=TODAY, provider=provider)

    # Then: the provider sees chunk-limited prompts and generated local suggestions keep source refs.
    assert provider.prompt_line_counts
    assert max(provider.prompt_line_counts) < 500
    assert all(count < len(text.splitlines()) for count in provider.prompt_line_counts)
    source_refs = [
        ref
        for item in payload["suggestions"]
        for ref in item["source_refs"]
    ]
    assert len(source_refs) <= 5 * max(1, len(payload["suggestions"]))
    assert any(900 <= ref["start_line"] <= 1100 for ref in source_refs)
    suggestion_kinds = {item["kind"] for item in payload["suggestions"]}
    assert {"source_candidate", "risk_candidate"} <= suggestion_kinds


def test_cli_assist_provider_runs_selected_adapter_and_parses_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts: list[str] = []

    def build_command(adapter: str, prompt: str) -> list[str] | None:
        prompts.append(prompt)
        return [adapter, "exec", prompt]

    monkeypatch.setattr(cli_adapters, "build_cli_command", build_command)
    runner = StubCliRunner(json.dumps({
        "schema_version": "report-assist-v1",
        "status": "ready",
        "suggestions": [{
            "id": "cli-risk-1",
            "finding_code": "missing_risk",
            "kind": "risk_candidate",
            "title": "운영 리스크",
            "proposed_text": "운영팀 확인이 늦어지면 배포 일정이 지연될 수 있어 사전 승인 일정을 둡니다.",
            "rationale": "원문 리스크 메모를 바탕으로 한 보완입니다.",
            "source_refs": [{"chunk_id": "chunk-1", "heading_path": ["리스크"], "start_line": 3, "end_line": 4}],
            "requires_user_confirmation": False,
        }],
        "questions": [],
        "applied_suggestion_ids": ["cli-risk-1"],
    }, ensure_ascii=False))
    provider = CliAssistProvider("codex", root=tmp_path, runner=runner)

    payload = provider.suggest({
        "finding_code": "missing_risk",
        "prompt": "Missing finding: missing_risk",
        "title": "예약 앱",
        "outline": ["# 예약 앱"],
        "chunks": [{
            "chunk_id": "chunk-1",
            "heading_path": ["리스크"],
            "start_line": 3,
            "end_line": 4,
            "text": "운영팀 확인이 늦어지면 배포 일정이 지연될 수 있습니다.",
            "signals": ["risk"],
        }],
    })

    assert runner.commands[0][0] == "codex"
    assert runner.cwd == tmp_path
    assert "입력 JSON" in prompts[0]
    assert payload["suggestions"][0]["finding_code"] == "missing_risk"
    assert payload["suggestions"][0]["requires_user_confirmation"] is True
    assert payload["applied_suggestion_ids"] == []


def test_assistance_contract_is_json_serializable() -> None:
    # Given: deterministic assistance for sparse input.
    payload = generate_report_assistance(_fixture("quality_sparse.md"), "proposal", date=TODAY)

    # When: serialized through the CLI JSON boundary shape.
    dumped = json.dumps({"assistance": payload}, ensure_ascii=False)

    # Then: the declared schema version remains stable.
    assert json.loads(dumped)["assistance"]["schema_version"] == "report-assist-v1"
