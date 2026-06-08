# vibelign/core/planning_cli/fallback.py
# === ANCHOR: FALLBACK_START ===
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.cli_adapters import PlanningCliRunner
from vibelign.core.planning_cli.personas import PlanningPersona
from vibelign.core.planning_cli.prompts import build_persona_prompt
from vibelign.core.planning_cli.response_policy import safe_planning_status

# 폴백 시도 우선순위. 사용자 지정 provider 가 항상 맨 앞에 오고,
# 그 뒤를 이 순서로 보충한다. v1 에서는 UI 비노출 내부 상수.
INTERNAL_PROVIDER_PRIORITY: tuple[str, ...] = ("claude", "codex", "agy", "opencode")


def provider_try_order(preferred: str | None) -> list[str]:
    """preferred 를 맨 앞에 두고 내부 우선순위로 보충한 시도 목록(중복 제거)."""
    order: list[str] = []
    if preferred:
        order.append(preferred)
    for provider in INTERNAL_PROVIDER_PRIORITY:
        if provider not in order:
            order.append(provider)
    return order


@dataclass(frozen=True)
class PersonaRun:
    adapter: str
    status: str
    stdout: str


# === ANCHOR: FALLBACK__RUN_PERSONA_WITH_FALLBACK_START ===
def run_persona_with_fallback(
    *,
    persona: PlanningPersona,
    preferred: str,
    runner: PlanningCliRunner,
    root: Path,
    message: str,
    markdown: str,
    timeout_seconds: int,
) -> PersonaRun:
    prompt = build_persona_prompt(persona, message, markdown)
    last_status = "not_installed"
    last_adapter = preferred
    for adapter in provider_try_order(preferred):
        command = cli_adapters.build_cli_command(adapter, prompt)
        if command is None:
            continue
        cli_result = runner.run(
            command, cwd=root, input_text="", timeout_seconds=timeout_seconds
        )
        status = safe_planning_status(cli_result.status, cli_result.stdout)
        last_adapter = adapter
        if status == "ok":
            return PersonaRun(adapter=adapter, status="ok", stdout=cli_result.stdout)
        last_status = status
    return PersonaRun(adapter=last_adapter, status=last_status, stdout="")
# === ANCHOR: FALLBACK__RUN_PERSONA_WITH_FALLBACK_END ===


# === ANCHOR: FALLBACK_END ===
