# === ANCHOR: DOCTOR_CMD_START ===
from pathlib import Path
from typing import Protocol

from vibelign.commands.vib_doctor_cmd import build_legacy_doctor_output
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


class DoctorArgs(Protocol):
    strict: bool
    json: bool


# === ANCHOR: DOCTOR_CMD_RUN_DOCTOR_START ===
def run_doctor(args: DoctorArgs) -> None:
    text, is_json = build_legacy_doctor_output(
        Path.cwd(), strict=args.strict, as_json=args.json
    )
    if is_json:
        print(text)
        return
    print_ai_response(text)


# === ANCHOR: DOCTOR_CMD_RUN_DOCTOR_END ===
# === ANCHOR: DOCTOR_CMD_END ===
