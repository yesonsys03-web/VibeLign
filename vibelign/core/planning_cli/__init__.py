from vibelign.core.planning_cli.models import PlanningInput, PlanningResult
from vibelign.core.planning_cli.storage import create_planning_template


def create_planning_with_persona(*args, **kwargs):
    from vibelign.core.planning_cli.engine import create_planning_with_persona as _create_planning_with_persona

    return _create_planning_with_persona(*args, **kwargs)


def append_planning_with_agents(*args, **kwargs):
    from vibelign.core.planning_cli.orchestrator import append_planning_with_agents as _append_planning_with_agents

    return _append_planning_with_agents(*args, **kwargs)


def create_planning_with_agents(*args, **kwargs):
    from vibelign.core.planning_cli.orchestrator import create_planning_with_agents as _create_planning_with_agents

    return _create_planning_with_agents(*args, **kwargs)


__all__ = [
    "PlanningInput",
    "PlanningResult",
    "append_planning_with_agents",
    "create_planning_with_agents",
    "create_planning_template",
    "create_planning_with_persona",
]
