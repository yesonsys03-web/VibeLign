from __future__ import annotations

from pathlib import Path

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.cli_adapters import (
    PlanningCliRunner,
    PlanningCliStatus,
    SubprocessPlanningCliRunner,
)
from vibelign.core.planning_cli.mentions import PersonaMentionResult, resolve_persona_mentions
from vibelign.core.planning_cli.models import PlanningInput, PlanningResult
from vibelign.core.planning_cli.personas import (
    PlanningPersona,
    ordered_personas_for_ids,
)
from vibelign.core.planning_cli.storage import create_planning_template

FORBIDDEN_LLM_TERMS = ("codespeak", "target_anchor", "patch")


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
    personas = _resolve_personas(mention_result, agents_choice)
    adapters = _resolve_adapters(cli_choice, personas)
    active_runner = runner or SubprocessPlanningCliRunner()
    markdown = base.markdown
    statuses: dict[str, str] = {}
    used_agents: list[str] = []

    for persona in personas:
        adapter = adapters[persona.id]
        command = cli_adapters.build_cli_command(
            adapter,
            _build_persona_prompt(persona, clean_input.idea, markdown),
        )
        if command is None:
            statuses[persona.id] = "not_installed"
            continue
        cli_result = active_runner.run(
            command,
            cwd=root,
            input_text="",
            timeout_seconds=timeout_seconds,
        )
        status = _safe_status(cli_result.status, cli_result.stdout)
        statuses[persona.id] = status
        if save_transcript:
            _save_transcript(root, base.session_id, persona.id, cli_result.stdout)
        if status != "ok":
            continue
        markdown = _append_persona_section(markdown, persona.section_title, cli_result.stdout)
        used_agents.append(persona.id)

    output_path = Path(base.absolute_output_path)
    output_path.write_text(markdown, encoding="utf-8")
    return _finalize_agent_result(
        base.with_markdown(markdown),
        personas=personas,
        adapters=adapters,
        statuses=statuses,
        used_agents=tuple(used_agents),
    )


def _resolve_personas(
    mention_result: PersonaMentionResult,
    agents_choice: str | None,
) -> tuple[PlanningPersona, ...]:
    persona_ids = (
        _parse_csv(agents_choice)
        if agents_choice
        else mention_result.persona_ids
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


def _build_persona_prompt(
    persona: PlanningPersona,
    idea: str,
    template_markdown: str,
) -> str:
    return "\n".join(
        [
            f"VibeLign 기획방의 {persona.prompt_role} 페르소나로 답하세요.",
            "초보자가 읽기 쉬운 한국어로 기획안을 보강하세요.",
            "불확실한 내용은 아직 결정이 필요한 질문으로 남기세요.",
            "프로젝트 전체 소스 코드를 요청하지 마세요.",
            "CodeSpeak, patch, target_anchor 용어를 쓰지 마세요.",
            "",
            f"사용자 아이디어: {idea.strip()}",
            "",
            "현재 기획안:",
            template_markdown,
        ]
    )


def _safe_status(status: PlanningCliStatus, stdout: str) -> str:
    if status == "ok" and _contains_forbidden_terms(stdout):
        return "bad_output"
    return status


def _contains_forbidden_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_LLM_TERMS)


def _append_persona_section(markdown: str, section_title: str, response: str) -> str:
    return f"{markdown.rstrip()}\n\n## {section_title}\n{response.strip()}\n"


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


def _save_transcript(root: Path, session_id: str, persona_id: str, response: str) -> None:
    transcript_dir = root / ".vibelign" / "planning" / session_id / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    (transcript_dir / f"{persona_id}.txt").write_text(response, encoding="utf-8")
