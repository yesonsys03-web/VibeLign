from vibelign.cli import build_parser
from vibelign.commands.vib_manual_cmd import MANUAL


def test_transfer_help_lists_handoff_override_flags() -> None:
    parser = build_parser()
    transfer_parser = parser._subparsers._group_actions[0].choices["transfer"]
    help_text = transfer_parser.format_help()

    assert "--session-summary" in help_text
    assert "--first-next-action" in help_text
    assert "--verification" in help_text
    assert "--decision" in help_text
    assert "--dry-run" in help_text


def test_transfer_manual_lists_handoff_override_flags() -> None:
    transfer = MANUAL["transfer"]
    examples = "\n".join(command for command, _ in transfer["examples"])
    options = "\n".join(name for name, _ in transfer["options"])

    assert "--session-summary" in examples
    assert "--first-next-action" in examples
    assert "--verification" in examples
    assert "--decision" in examples
    assert "--session-summary" in options
    assert "--first-next-action" in options
    assert "--verification" in options
    assert "--decision" in options
