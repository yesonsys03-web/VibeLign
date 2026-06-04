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


def test_manual_removes_legacy_patch_and_plan_structure_sections() -> None:
    manual = (ROOT / "docs" / "MANUAL.md").read_text(encoding="utf-8")

    assert "## `vib patch`" not in manual
    assert "## `vib plan-structure`" not in manual
    assert "plan-structure" not in manual
    assert "CodeSpeak" not in manual
    assert "target_file" not in manual
    assert "target_anchor" not in manual


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
    assert "`vib patch`" not in command_guide


def test_active_rules_and_docs_use_direct_read_workflow() -> None:
    paths = [
        ROOT / "AGENTS.md",
        ROOT / "AI_DEV_SYSTEM_SINGLE_FILE.md",
        ROOT / "VibeLign_QUICKSTART.md",
        ROOT / "docs" / "MANUAL.md",
        ROOT / "docs" / "wiki" / "command-guide.md",
        ROOT / "docs" / "wiki" / "getting-started.md",
        ROOT / "docs" / "wiki" / "core-workflow.md",
    ]
    active_text = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "project_map_get" in active_text
    assert "anchor_read_content" in active_text
    for removed in [
        "patch_get",
        "patch_apply",
        "CodeSpeak",
        "target_file",
        "target_anchor",
        "vib patch",
        "plan-structure",
    ]:
        assert removed not in active_text
