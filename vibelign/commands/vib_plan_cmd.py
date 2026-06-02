from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.planning_cli import (
    PlanningInput,
    append_planning_with_agents,
    create_planning_with_agents,
    create_planning_template,
)
from vibelign.core.planning_cli.cli_adapters import SubprocessPlanningCliRunner
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import clack_intro, clack_step, clack_success


class PlanArgs(Protocol):
    idea: Sequence[str] | str
    template_only: bool
    append_to: str | None
    output: str | None
    force: bool
    language: str
    json: bool
    cli: str
    agents: str | None
    save_transcript: bool
    llm_timeout_seconds: int


def _idea_text(raw_idea: Sequence[str] | str) -> str:
    if isinstance(raw_idea, str):
        return raw_idea.strip()
    return " ".join(str(item).strip() for item in raw_idea if str(item).strip()).strip()


def run_vib_plan(args: object) -> None:
    raw_args = cast(PlanArgs, args)
    idea = _idea_text(raw_args.idea)
    if not idea:
        raise SystemExit('기획할 내용을 입력하세요. 예: vib plan "예약 앱 만들고 싶어"')

    root = resolve_project_root(Path.cwd())
    planning_input = PlanningInput(
        idea=idea,
        language=raw_args.language or "auto",
        output=raw_args.output,
        force=bool(raw_args.force),
    )
    if getattr(raw_args, "append_to", None):
        result = append_planning_with_agents(
            root,
            output_path=str(raw_args.append_to),
            message=idea,
            agents_choice=getattr(raw_args, "agents", None),
            cli_choice=raw_args.cli or "auto",
            timeout_seconds=int(raw_args.llm_timeout_seconds),
            save_transcript=bool(getattr(raw_args, "save_transcript", False)),
            runner=SubprocessPlanningCliRunner(),
        )
    elif bool(raw_args.template_only):
        result = create_planning_template(root, planning_input)
    else:
        result = create_planning_with_agents(
            root,
            planning_input,
            agents_choice=getattr(raw_args, "agents", None),
            cli_choice=raw_args.cli or "auto",
            timeout_seconds=int(raw_args.llm_timeout_seconds),
            save_transcript=bool(getattr(raw_args, "save_transcript", False)),
            runner=SubprocessPlanningCliRunner(),
        )

    if bool(raw_args.json):
        print(
            json.dumps(
                {
                    "ok": True,
                    "output_path": result.output_path,
                    "absolute_output_path": result.absolute_output_path,
                    "markdown": result.markdown,
                    "fallback_reason": result.fallback_reason,
                    "session_id": result.session_id,
                    "adapter": result.adapter,
                    "persona_id": result.persona_id,
                    "llm_status": result.llm_status,
                    "agents_requested": list(result.agents_requested),
                    "agents_used": list(result.agents_used),
                    "agent_statuses": result.agent_statuses or {},
                },
                ensure_ascii=False,
            )
        )
        return

    clack_intro("VibeLign 기획안")
    clack_step("기획안 생성")
    clack_success(f"기획안 저장: {result.output_path}")
