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
from vibelign.core.planning_cli.prompts import append_persona_section, build_persona_prompt
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
    command = build_codex_command(build_persona_prompt(persona, planning_input.idea, base.markdown))
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

    markdown = append_persona_section(base.markdown, persona.section_title, cli_result.stdout)
    output_path = Path(base.absolute_output_path)
    output_path.write_text(markdown, encoding="utf-8")
    return base.with_markdown(markdown).with_llm_status(
        adapter=adapter,
        persona_id=persona.id,
        llm_status="ok",
        fallback_reason=None,
    )


def _contains_forbidden_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_LLM_TERMS)
