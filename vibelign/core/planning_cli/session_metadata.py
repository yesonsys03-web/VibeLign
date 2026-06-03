from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


@dataclass(frozen=True, slots=True)
class AgentRunMetadata:
    turn_index: int
    persona_id: str
    cli_id: str
    status: str
    response: str


class AgentRunJson(TypedDict):
    run_id: str
    turn_id: str
    persona_id: str
    cli_id: str
    status: str
    summary: str


class PlanningSessionJson(TypedDict, total=False):
    schema_version: int
    session_id: str
    idea: str
    language: str
    output_path: str
    fallback_reason: str | None
    created_at: str
    agents_requested: list[str]
    agents_used: list[str]
    agent_statuses: dict[str, str]
    runs: list[AgentRunJson]


def write_agent_session_metadata(
    root: Path,
    *,
    session_id: str,
    agents_requested: tuple[str, ...],
    agents_used: tuple[str, ...],
    agent_statuses: dict[str, str],
    runs: tuple[AgentRunMetadata, ...],
) -> None:
    session_path = root / ".vibelign" / "planning" / session_id / "session.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session: PlanningSessionJson
    if session_path.exists():
        session = json.loads(session_path.read_text(encoding="utf-8"))
    else:
        session = {"schema_version": 1, "session_id": session_id}
    session["agents_requested"] = list(agents_requested)
    session["agents_used"] = list(agents_used)
    session["agent_statuses"] = dict(agent_statuses)
    session["runs"] = [_run_to_json(run) for run in runs]
    session_path.write_text(
        json.dumps(session, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _run_to_json(run: AgentRunMetadata) -> AgentRunJson:
    turn_id = f"turn_{run.turn_index:03d}"
    return {
        "run_id": f"run_{run.persona_id}_{run.turn_index:03d}",
        "turn_id": turn_id,
        "persona_id": run.persona_id,
        "cli_id": run.cli_id,
        "status": run.status,
        "summary": _compact_summary(run.response),
    }


def _compact_summary(response: str) -> str:
    normalized = " ".join(response.strip().split())
    if len(normalized) <= 120:
        return normalized
    return f"{normalized[:117]}..."
