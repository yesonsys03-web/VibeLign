from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.planning_cli import PlanningInput, create_planning_template
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import clack_intro, clack_step, clack_success


class PlanArgs(Protocol):
    idea: Sequence[str] | str
    template_only: bool
    output: str | None
    force: bool
    language: str
    json: bool


def _idea_text(raw_idea: Sequence[str] | str) -> str:
    if isinstance(raw_idea, str):
        return raw_idea.strip()
    return " ".join(str(item).strip() for item in raw_idea if str(item).strip()).strip()


def run_vib_plan(args: object) -> None:
    raw_args = cast(PlanArgs, args)
    idea = _idea_text(raw_args.idea)
    if not idea:
        raise SystemExit('기획할 내용을 입력하세요. 예: vib plan "예약 앱 만들고 싶어"')
    if not bool(raw_args.template_only):
        raise SystemExit("PR 3에서는 --template-only만 지원합니다.")

    root = resolve_project_root(Path.cwd())
    result = create_planning_template(
        root,
        PlanningInput(
            idea=idea,
            language=raw_args.language or "auto",
            output=raw_args.output,
            force=bool(raw_args.force),
        ),
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
                },
                ensure_ascii=False,
            )
        )
        return

    clack_intro("VibeLign 기획안")
    clack_step("템플릿 기획안 생성")
    clack_success(f"기획안 저장: {result.output_path}")
