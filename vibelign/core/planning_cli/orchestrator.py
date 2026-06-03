from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.cli_adapters import (
    PlanningCliRunner,
    SubprocessPlanningCliRunner,
)
from vibelign.core.planning_cli.mentions import resolve_persona_mentions
from vibelign.core.planning_cli.models import PlanningInput, PlanningResult
from vibelign.core.planning_cli.personas import (
    PlanningPersona,
    ordered_personas_for_ids,
)
from vibelign.core.planning_cli.prompts import append_persona_section, build_persona_prompt
from vibelign.core.planning_cli.response_policy import safe_planning_status
from vibelign.core.planning_cli.session_metadata import (
    AgentRunMetadata,
    write_agent_session_metadata,
)
from vibelign.core.planning_cli.storage import create_planning_template
from vibelign.core.planning_cli.transcripts import write_turn_transcript


def create_planning_with_agents(
    root: Path,
    planning_input: PlanningInput,
    *,
    agents_choice: str | None = None,
    cli_choice: str = "auto",
    timeout_seconds: int = 300,
    save_transcript: bool = False,
    runner: PlanningCliRunner | None = None,
) -> PlanningResult:
    mention_result = resolve_persona_mentions(planning_input.idea)
    clean_input = PlanningInput(
        idea=mention_result.clean_text or planning_input.idea,
        language=planning_input.language,
        output=planning_input.output,
        force=planning_input.force,
    )
    base = create_planning_template(root, clean_input)
    return _apply_agents_to_result(
        root,
        base,
        message=clean_input.idea,
        agents_choice=agents_choice,
        default_persona_ids=mention_result.persona_ids,
        cli_choice=cli_choice,
        timeout_seconds=timeout_seconds,
        save_transcript=save_transcript,
        runner=runner,
    )


def append_planning_with_agents(
    root: Path,
    *,
    output_path: str,
    message: str,
    agents_choice: str | None = None,
    cli_choice: str = "auto",
    timeout_seconds: int = 300,
    save_transcript: bool = False,
    runner: PlanningCliRunner | None = None,
) -> PlanningResult:
    root = root.resolve()
    relative_path = _safe_relative_output_path(output_path)
    absolute_path = root / relative_path
    markdown = absolute_path.read_text(encoding="utf-8")
    base = PlanningResult(
        output_path=relative_path.as_posix(),
        absolute_output_path=str(absolute_path),
        markdown=markdown,
        fallback_reason=None,
        session_id=f"followup_{uuid4().hex[:8]}",
    )
    return _apply_agents_to_result(
        root,
        base,
        message=message,
        agents_choice=agents_choice,
        default_persona_ids=None,
        cli_choice=cli_choice,
        timeout_seconds=timeout_seconds,
        save_transcript=save_transcript,
        runner=runner,
    )


def _apply_agents_to_result(
    root: Path,
    base: PlanningResult,
    *,
    message: str,
    agents_choice: str | None,
    default_persona_ids: tuple[str, ...] | None,
    cli_choice: str,
    timeout_seconds: int,
    save_transcript: bool,
    runner: PlanningCliRunner | None,
) -> PlanningResult:
    mention_result = resolve_persona_mentions(message)
    personas = _resolve_personas(
        default_persona_ids or mention_result.persona_ids,
        agents_choice,
    )
    adapters = _resolve_adapters(cli_choice, personas)
    active_runner = runner or SubprocessPlanningCliRunner()
    markdown = base.markdown
    statuses: dict[str, str] = {}
    used_agents: list[str] = []
    runs: list[AgentRunMetadata] = []

    for turn_index, persona in enumerate(personas, start=1):
        adapter = adapters[persona.id]
        command = cli_adapters.build_cli_command(
            adapter,
            build_persona_prompt(persona, mention_result.clean_text or message, markdown),
        )
        if command is None:
            statuses[persona.id] = "not_installed"
            runs.append(AgentRunMetadata(turn_index, persona.id, adapter, "not_installed", ""))
            continue
        cli_result = active_runner.run(
            command,
            cwd=root,
            input_text="",
            timeout_seconds=timeout_seconds,
        )
        status = safe_planning_status(cli_result.status, cli_result.stdout)
        statuses[persona.id] = status
        runs.append(AgentRunMetadata(turn_index, persona.id, adapter, status, cli_result.stdout))
        if save_transcript:
            write_turn_transcript(
                root,
                session_id=base.session_id,
                turn_index=turn_index,
                adapter=adapter,
                response=cli_result.stdout,
            )
        if status != "ok":
            continue
        markdown = append_persona_section(markdown, persona.section_title, cli_result.stdout)
        used_agents.append(persona.id)

    output_path = Path(base.absolute_output_path)
    output_path.write_text(markdown, encoding="utf-8")
    final_result = _finalize_agent_result(
        base.with_markdown(markdown),
        personas=personas,
        adapters=adapters,
        statuses=statuses,
        used_agents=tuple(used_agents),
    )
    write_agent_session_metadata(
        root,
        session_id=base.session_id,
        agents_requested=final_result.agents_requested,
        agents_used=final_result.agents_used,
        agent_statuses=statuses,
        runs=tuple(runs),
    )
    return final_result


def _resolve_personas(
    default_persona_ids: tuple[str, ...],
    agents_choice: str | None,
) -> tuple[PlanningPersona, ...]:
    persona_ids = (
        _parse_csv(agents_choice)
        if agents_choice
        else default_persona_ids
    )
    return ordered_personas_for_ids(persona_ids)


def _resolve_adapters(
    cli_choice: str,
    personas: tuple[PlanningPersona, ...],
) -> dict[str, str]:
    cli_ids = _parse_csv(cli_choice)
    if not cli_ids or cli_ids == ("auto",):
        return {persona.id: persona.adapter for persona in personas}
    if len(cli_ids) == 1:
        adapter = cli_adapters.select_adapter(cli_ids[0])
        return {persona.id: adapter for persona in personas}
    mapped: dict[str, str] = {}
    for index, persona in enumerate(personas):
        mapped[persona.id] = (
            cli_adapters.select_adapter(cli_ids[index])
            if index < len(cli_ids)
            else persona.adapter
        )
    return mapped


def _parse_csv(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    return tuple(item.strip().lower() for item in raw.split(",") if item.strip())


def _safe_relative_output_path(raw_path: str) -> Path:
    relative_path = Path(raw_path)
    if relative_path.is_absolute() or any(part == ".." for part in relative_path.parts):
        raise ValueError("append_to must be a project-relative path")
    return relative_path


def _finalize_agent_result(
    base: PlanningResult,
    *,
    personas: tuple[PlanningPersona, ...],
    adapters: dict[str, str],
    statuses: dict[str, str],
    used_agents: tuple[str, ...],
) -> PlanningResult:
    first_persona = personas[0] if personas else None
    persona_id = used_agents[0] if used_agents else (
        first_persona.id if first_persona is not None else None
    )
    adapter = adapters[persona_id] if persona_id is not None else None
    llm_status = statuses.get(persona_id) if persona_id is not None else None
    fallback_reason = None if used_agents else "cli_unavailable_template_only"
    return base.with_agents(
        agents_requested=tuple(persona.id for persona in personas),
        agents_used=used_agents,
        agent_statuses=statuses,
        adapter=adapter,
        persona_id=persona_id,
        llm_status=llm_status,
        fallback_reason=fallback_reason,
    )
