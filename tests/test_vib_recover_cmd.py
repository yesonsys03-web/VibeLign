from dataclasses import dataclass
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_recover_cmd import run_vib_recover
from vibelign.core.recovery.apply import RecoveryApplyRequest


@dataclass
class _RecoverArgs:
    explain: bool
    preview: bool = False
    file: str | None = None
    apply: bool = False
    checkpoint_id: str = ""
    sandwich_checkpoint_id: str = ""
    confirmation: str = ""


@dataclass
class _RecoverApplyResult:
    ok: bool
    changed_files_count: int
    changed_files: list[str]
    safety_checkpoint_id: str
    operation_id: str
    errors: list[str]


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


def test_run_vib_recover_preview_is_read_only_alias(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    _ = (root / ".vibelign").mkdir()
    _ = (root / "app.py").write_text("print('ok')\n", encoding="utf-8")

    with patch("pathlib.Path.cwd", return_value=root), patch(
        "vibelign.commands.vib_recover_cmd.print"
    ) as mocked_print:
        run_vib_recover(_RecoverArgs(explain=False, preview=True))

    output = "\n".join(cast(str, call.args[0]) for call in mocked_print.call_args_list)
    assert "VibeLign Recovery Advisor (read-only)" in output
    assert "No files were modified." in output
    assert not (root / ".vibelign" / "recovery").exists()


def test_run_vib_recover_file_preview_is_read_only(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    _ = (root / ".vibelign").mkdir()
    _ = (root / "src").mkdir()
    _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

    with patch("pathlib.Path.cwd", return_value=root), patch(
        "vibelign.commands.vib_recover_cmd.print"
    ) as mocked_print:
        run_vib_recover(_RecoverArgs(explain=False, file="src/app.py"))

    output = "\n".join(cast(str, call.args[0]) for call in mocked_print.call_args_list)
    assert "VibeLign Recovery Advisor (read-only)" in output
    assert "Selected file preview target: src/app.py" in output
    assert "No files were modified." in output
    assert not (root / ".vibelign" / "recovery").exists()


def test_run_vib_recover_file_preview_rejects_unsafe_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    _ = (root / ".vibelign").mkdir()

    with patch("pathlib.Path.cwd", return_value=root), patch(
        "vibelign.commands.vib_recover_cmd.print"
    ) as mocked_print:
        run_vib_recover(_RecoverArgs(explain=False, file="../secret.py"))

    output = "\n".join(cast(str, call.args[0]) for call in mocked_print.call_args_list)
    assert "VibeLign Recovery Advisor (read-only)" in output
    assert "Invalid recovery file target" in output
    assert "recovery path must stay inside project root" in output
    assert "No files were modified." in output
    assert not (root / ".vibelign" / "recovery").exists()


def test_run_vib_recover_apply_routes_to_core_apply(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    with patch("pathlib.Path.cwd", return_value=root), patch(
        "vibelign.commands.vib_recover_cmd.execute_recovery_apply"
    ) as execute_mock, patch("vibelign.commands.vib_recover_cmd.print") as mocked_print:
        execute_mock.return_value = _RecoverApplyResult(
            ok=True,
            changed_files_count=1,
            changed_files=["src/app.py"],
            safety_checkpoint_id="ckpt_safety",
            operation_id="lock_1",
            errors=[],
        )
        run_vib_recover(
            _RecoverArgs(
                explain=False,
                file="src/app.py",
                apply=True,
                checkpoint_id="ckpt_before",
                sandwich_checkpoint_id="ckpt_safety",
                confirmation="APPLY ckpt_before",
            )
        )

    request = cast(RecoveryApplyRequest, execute_mock.call_args.args[1])
    assert request.checkpoint_id == "ckpt_before"
    assert request.sandwich_checkpoint_id == "ckpt_safety"
    assert request.paths == ["src/app.py"]
    assert request.preview_paths == ["src/app.py"]
    assert request.confirmation == "APPLY ckpt_before"
    assert request.apply is True
    output = "\n".join(cast(str, call.args[0]) for call in mocked_print.call_args_list)
    assert "Recovery apply completed" in output
    assert "changed files: 1" in output


def test_run_vib_recover_without_explain_points_to_explain_mode() -> None:
    with patch("vibelign.commands.vib_recover_cmd.print") as mocked_print:
        run_vib_recover(_RecoverArgs(explain=False, preview=False))

    assert mocked_print.call_args is not None
    message = cast(str, mocked_print.call_args.args[0])
    assert "vib recover --explain" in message
    assert "vib recover --preview" in message
    assert "vib recover --file" in message
