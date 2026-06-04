from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_first_flow_does_not_recommend_legacy_patch_surface() -> None:
    first_flow = "\n".join(
        (ROOT / "README.md").read_text(encoding="utf-8").splitlines()[:220]
    )

    assert "vib patch" not in first_flow
    assert "CodeSpeak" not in first_flow
    assert "plan-structure" not in first_flow


def test_korean_readme_first_flow_does_not_recommend_legacy_patch_surface() -> None:
    first_flow = "\n".join(
        (ROOT / "README.ko.md").read_text(encoding="utf-8").splitlines()[:220]
    )

    assert "vib patch" not in first_flow
    assert "CodeSpeak" not in first_flow
    assert "plan-structure" not in first_flow


def test_manual_marks_patch_and_plan_structure_as_legacy() -> None:
    manual = (ROOT / "docs" / "MANUAL.md").read_text(encoding="utf-8")

    patch_section = manual.split("## `vib patch`", maxsplit=1)[1].split("## `vib explain`", maxsplit=1)[0]
    plan_structure_section = manual.split("## `vib plan-structure`", maxsplit=1)[1].split("## `vib transfer`", maxsplit=1)[0]

    assert "legacy" in patch_section.lower()
    assert "legacy" in plan_structure_section.lower()


def test_docs_wiki_first_flows_do_not_recommend_legacy_patch_surface() -> None:
    getting_started = (ROOT / "docs" / "wiki" / "getting-started.md").read_text(
        encoding="utf-8"
    )
    core_workflow = (ROOT / "docs" / "wiki" / "core-workflow.md").read_text(
        encoding="utf-8"
    )
    command_guide = (ROOT / "docs" / "wiki" / "command-guide.md").read_text(
        encoding="utf-8"
    )

    assert "vib patch" not in getting_started
    assert "vib patch" not in core_workflow
    assert "`vib patch`" not in command_guide.split("## Legacy Commands", maxsplit=1)[0]
