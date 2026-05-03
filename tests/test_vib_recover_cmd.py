from dataclasses import dataclass
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_recover_cmd import run_vib_recover


@dataclass
class _RecoverArgs:
    explain: bool


def test_run_vib_recover_explain_is_read_only(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    _ = (root / ".vibelign").mkdir()
    _ = (root / "app.py").write_text("print('ok')\n", encoding="utf-8")

    with patch("pathlib.Path.cwd", return_value=root), patch(
        "vibelign.commands.vib_recover_cmd.print"
    ) as mocked_print:
        run_vib_recover(_RecoverArgs(explain=True))

    output = "\n".join(cast(str, call.args[0]) for call in mocked_print.call_args_list)
    assert "VibeLign Recovery Advisor (read-only)" in output
    assert "No files were modified." in output
    assert not (root / ".vibelign" / "state.json").exists()


def test_run_vib_recover_without_explain_points_to_explain_mode() -> None:
    with patch("vibelign.commands.vib_recover_cmd.print") as mocked_print:
        run_vib_recover(_RecoverArgs(explain=False))

    assert mocked_print.call_args is not None
    message = cast(str, mocked_print.call_args.args[0])
    assert "vib recover --explain" in message
