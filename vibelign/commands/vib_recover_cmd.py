# === ANCHOR: VIB_RECOVER_CMD_START ===
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vibelign.core.project_root import resolve_project_root
from vibelign.core.recovery.planner import build_recovery_plan
from vibelign.core.recovery.render import render_text_plan
from vibelign.core.recovery.signals import collect_basic_signals
from vibelign.terminal_render import cli_print

print = cli_print


class RecoverArgs(Protocol):
    explain: bool


# === ANCHOR: VIB_RECOVER_CMD__RUN_VIB_RECOVER_START ===
def run_vib_recover(args: RecoverArgs) -> None:
    if not getattr(args, "explain", False):
        print("Recovery Advisor is read-only in Phase 1. Run: vib recover --explain")
        return

    project_root = resolve_project_root(Path.cwd())
    signals = collect_basic_signals(project_root)
    plan = build_recovery_plan(signals)
    print(render_text_plan(plan))
# === ANCHOR: VIB_RECOVER_CMD__RUN_VIB_RECOVER_END ===

# === ANCHOR: VIB_RECOVER_CMD_END ===
