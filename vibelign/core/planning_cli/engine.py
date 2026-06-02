from __future__ import annotations

from pathlib import Path

from vibelign.core.planning_cli.cli_adapters import (
    PlanningCliRunner,
    SubprocessPlanningCliRunner,
    build_codex_command,
    select_adapter,
)
from vibelign.core.planning_cli.models import PlanningInput, PlanningResult
from vibelign.core.planning_cli.personas import persona_for_adapter
from vibelign.core.planning_cli.storage import create_planning_template

FORBIDDEN_LLM_TERMS = ("codespeak", "target_anchor", "patch")


def create_planning_with_persona(
    root: Path,
    planning_input: PlanningInput,
    *,
    cli_choice: str = "auto",
    timeout_seconds: int = 300,
    runner: PlanningCliRunner | None = None,
) -> PlanningResult:
    base = create_planning_template(root, planning_input)
    adapter = select_adapter(cli_choice)
    persona = persona_for_adapter(adapter)
    command = build_codex_command(_build_persona_prompt(planning_input.idea, base.markdown))
    if command is None:
        return base.with_llm_status(
            adapter=adapter,
            persona_id=persona.id,
            llm_status="not_installed",
            fallback_reason="cli_unavailable_template_only",
        )

    active_runner = runner or SubprocessPlanningCliRunner()
    cli_result = active_runner.run(
        command,
        cwd=root,
        input_text="",
        timeout_seconds=timeout_seconds,
    )
    if cli_result.status != "ok" or _contains_forbidden_terms(cli_result.stdout):
        status = "bad_output" if cli_result.status == "ok" else cli_result.status
        return base.with_llm_status(
            adapter=adapter,
            persona_id=persona.id,
            llm_status=status,
            fallback_reason="cli_unavailable_template_only",
        )

    markdown = _append_persona_review(base.markdown, persona.name, cli_result.stdout)
    output_path = Path(base.absolute_output_path)
    output_path.write_text(markdown, encoding="utf-8")
    return base.with_markdown(markdown).with_llm_status(
        adapter=adapter,
        persona_id=persona.id,
        llm_status="ok",
        fallback_reason=None,
    )


def _build_persona_prompt(idea: str, template_markdown: str) -> str:
    return "\n".join(
        [
            "VibeLign 기획방의 지오 페르소나로 답하세요.",
            "초보자가 읽기 쉬운 한국어로 기획안을 보강하세요.",
            "불확실한 내용은 아직 결정이 필요한 질문으로 남기세요.",
            "프로젝트 전체 소스 코드를 요청하지 마세요.",
            "CodeSpeak, patch, target_anchor 용어를 쓰지 마세요.",
            "",
            f"사용자 아이디어: {idea.strip()}",
            "",
            "현재 템플릿 기획안:",
            template_markdown,
        ]
    )


def _contains_forbidden_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_LLM_TERMS)


def _append_persona_review(markdown: str, persona_name: str, review: str) -> str:
    clean_review = review.strip()
    return f"{markdown.rstrip()}\n\n## {persona_name}의 검토\n{clean_review}\n"
