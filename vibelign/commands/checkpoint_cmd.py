# === ANCHOR: CHECKPOINT_CMD_START ===
from argparse import Namespace
from typing import cast

from vibelign.commands.vib_checkpoint_cmd import run_vib_checkpoint


# === ANCHOR: CHECKPOINT_CMD_RUN_CHECKPOINT_START ===
def run_checkpoint(args: Namespace) -> None:
    message_value = getattr(args, "message", [])
    message = (
        cast(list[object], message_value) if isinstance(message_value, list) else []
    )
    run_vib_checkpoint(Namespace(message=message, json=False))


# === ANCHOR: CHECKPOINT_CMD_RUN_CHECKPOINT_END ===
# === ANCHOR: CHECKPOINT_CMD_END ===
