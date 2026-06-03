from pathlib import Path


def test_orchestrator_stays_within_component_boundary() -> None:
    orchestrator = Path("vibelign/core/planning_cli/orchestrator.py")

    pure_loc = sum(
        1
        for line in orchestrator.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )

    assert pure_loc <= 220
