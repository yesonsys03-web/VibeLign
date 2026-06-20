# === ANCHOR: VIB_REPORT_CMD_START ===
from __future__ import annotations

from vibelign.commands.vib_report_runtime import ReportArgs, run_report_command
from vibelign.core.reporting_cli import polish_report_model


# === ANCHOR: VIB_REPORT_CMD_REPORTARGS_START ===
__all__ = ["ReportArgs", "run_vib_report"]
# === ANCHOR: VIB_REPORT_CMD_REPORTARGS_END ===


# === ANCHOR: VIB_REPORT_CMD_RUN_VIB_REPORT_START ===
def run_vib_report(raw: ReportArgs) -> None:
    run_report_command(raw, polish_report_model)
# === ANCHOR: VIB_REPORT_CMD_RUN_VIB_REPORT_END ===
# === ANCHOR: VIB_REPORT_CMD_END ===
