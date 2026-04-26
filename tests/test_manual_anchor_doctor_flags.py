from pathlib import Path

from vibelign.commands.vib_manual_cmd import MANUAL


ManualPairs = list[tuple[str, str]]


def _examples(command_name: str) -> str:
    command = MANUAL[command_name]
    examples = command.get("examples", [])
    return "\n".join(example for example, _ in examples)


def _options(command_name: str) -> str:
    command = MANUAL[command_name]
    options = command.get("options", [])
    return "\n".join(option for option, _ in options)


def test_doctor_manual_lists_fix_anchor_flags() -> None:
    examples = _examples("doctor")
    options = _options("doctor")

    assert "--fix-anchors --dry-run" in examples
    assert "--fix-anchors --paths src/app.py" in examples
    assert "--fix-anchors" in options
    assert "--dry-run" in options
    assert "--paths src/app.py" in options


def test_anchor_manual_lists_path_and_module_only_flags() -> None:
    examples = _examples("anchor")
    options = _options("anchor")

    assert "--auto --paths src/app.py" in examples
    assert "--auto --module-only --paths src/app.py" in examples
    assert "--paths src/app.py" in options
    assert "--module-only" in options


def test_anchor_manual_lists_all_anchor_subflags() -> None:
    options = _options("anchor")
    expected_flags = [
        "--help",
        "--suggest",
        "--auto",
        "--module-only",
        "--paths",
        "--validate",
        "--dry-run",
        "--json",
        "--only-ext",
        "--set-intent",
        "--intent",
        "--list-intent",
        "--auto-intent",
        "--force",
        "--with-ai",
        "--aliases",
        "--description",
        "--warning",
        "--connects",
    ]

    for flag in expected_flags:
        assert flag in options


def test_saved_manual_lists_anchor_and_doctor_flags() -> None:
    manual_text = Path("VIBELIGN_MANUAL.md").read_text(encoding="utf-8")

    assert "vib doctor --fix-anchors --dry-run" in manual_text
    assert "vib doctor --fix-anchors --paths src/app.py" in manual_text
    assert "vib anchor --auto --paths src/app.py" in manual_text
    assert "vib anchor --auto --module-only --paths src/app.py" in manual_text
    for flag in [
        "--help",
        "--suggest",
        "--auto",
        "--module-only",
        "--paths src/app.py",
        "--validate",
        "--dry-run",
        "--json",
        "--only-ext .py",
        "--set-intent ANCHOR_NAME",
        "--intent TEXT",
        "--list-intent",
        "--auto-intent",
        "--force",
        "--with-ai",
        "--aliases A,B,C",
        "--description TEXT",
        "--warning TEXT",
        "--connects A,B,C",
    ]:
        assert flag in manual_text
