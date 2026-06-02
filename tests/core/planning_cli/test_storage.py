import json
from pathlib import Path

import pytest

from vibelign.core.planning_cli.models import PlanningInput
from vibelign.core.planning_cli.storage import create_planning_template, safe_plan_slug


def test_create_template_writes_root_plans_and_session(tmp_path: Path) -> None:
    result = create_planning_template(tmp_path, PlanningInput(idea="예약 앱"))

    assert result.output_path.startswith("plans/")
    assert (tmp_path / result.output_path).exists()
    assert not (tmp_path / ".vibelign" / "plans").exists()
    session_path = tmp_path / ".vibelign" / "planning" / result.session_id / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    assert session["fallback_reason"] == "template_only"


def test_create_template_adds_collision_suffix(tmp_path: Path) -> None:
    first = create_planning_template(tmp_path, PlanningInput(idea="예약 앱"))
    second = create_planning_template(tmp_path, PlanningInput(idea="예약 앱"))

    assert first.output_path == "plans/예약-앱.md"
    assert second.output_path == "plans/예약-앱-2.md"


def test_output_existing_requires_force(tmp_path: Path) -> None:
    target = tmp_path / "plans" / "custom.md"
    target.parent.mkdir()
    target.write_text("old", encoding="utf-8")

    with pytest.raises(FileExistsError):
        create_planning_template(tmp_path, PlanningInput(idea="예약 앱", output="plans/custom.md"))

    result = create_planning_template(
        tmp_path,
        PlanningInput(idea="예약 앱", output="plans/custom.md", force=True),
    )
    assert result.output_path == "plans/custom.md"
    assert target.read_text(encoding="utf-8").startswith("# 예약 앱")


def test_safe_slug_avoids_reserved_names() -> None:
    assert safe_plan_slug("CON") == "plan"
    assert safe_plan_slug("<>:/\\|?*") == "plan"
