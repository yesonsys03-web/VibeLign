# === ANCHOR: VIB_RECOVER_CMD_START ===
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vibelign.core.project_root import resolve_project_root
from vibelign.core.recovery.apply import RecoveryApplyRequest, execute_recovery_apply
from vibelign.core.recovery.path import PathSafetyError, normalize_recovery_path
from vibelign.core.recovery.planner import build_recovery_plan
from vibelign.core.recovery.render import render_text_plan
from vibelign.core.recovery.signals import collect_basic_signals
from vibelign.terminal_render import cli_print

print = cli_print

_RECOVER_HELP = "Recovery Advisor is read-only. Run: vib recover --explain, vib recover --preview, or vib recover --file <path>"


class RecoverArgs(Protocol):
    explain: bool
    preview: bool
    file: str | None
    apply: bool
    checkpoint_id: str
    sandwich_checkpoint_id: str
    confirmation: str


# === ANCHOR: VIB_RECOVER_CMD__RUN_VIB_RECOVER_START ===
def run_vib_recover(args: RecoverArgs) -> None:
    file_target = args.file
    if not (args.explain or args.preview or file_target):
        print(_RECOVER_HELP)
        return

    project_root = resolve_project_root(Path.cwd())
    if args.apply:
        print(_run_file_apply(project_root, args))
        return

    signals = collect_basic_signals(project_root)
    plan = build_recovery_plan(signals)
    output = render_text_plan(plan)
    if file_target:
        output = f"{output}\n\n{_render_file_preview(project_root, file_target)}"
    print(output)
# === ANCHOR: VIB_RECOVER_CMD__RUN_VIB_RECOVER_END ===


def _render_file_preview(project_root: Path, file_target: str) -> str:
    try:
        normalized = normalize_recovery_path(
            project_root,
            file_target,
            trusted_local_cli=True,
        )
    except PathSafetyError as exc:
        return f"Invalid recovery file target: {exc}"
    return (
        f"Selected file preview target: {normalized.display_path}\n"
        "Apply is not enabled; inspect this target before any restore."
    )


def _run_file_apply(project_root: Path, args: RecoverArgs) -> str:
    file_target = args.file or ""
    result = execute_recovery_apply(
        project_root,
        RecoveryApplyRequest(
            checkpoint_id=args.checkpoint_id,
            sandwich_checkpoint_id=args.sandwich_checkpoint_id,
            paths=[file_target] if file_target else [],
            preview_paths=[file_target] if file_target else [],
            confirmation=args.confirmation,
            apply=True,
        ),
    )
    if not result.ok:
        errors = "; ".join(result.errors) or "recovery apply failed"
        return f"Recovery apply blocked\nNo files were modified.\nErrors: {errors}"
    return (
        "Recovery apply completed\n"
        f"changed files: {result.changed_files_count}\n"
        f"safety checkpoint: {result.safety_checkpoint_id}\n"
        f"operation: {result.operation_id}"
    )

# === ANCHOR: VIB_RECOVER_CMD_END ===
