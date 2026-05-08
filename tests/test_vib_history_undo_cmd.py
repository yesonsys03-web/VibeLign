from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_history_cmd import run_vib_history
from vibelign.commands.vib_undo_cmd import run_vib_undo
from vibelign.core.checkpoint_engine.rust_engine import RustEngineResult


def _rust_ok(payload: dict[str, object]) -> RustEngineResult:
    return RustEngineResult(ok=True, payload=payload)


def _list_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "result": "listed",
        "checkpoints": [
            {
                "checkpoint_id": "cp-cli-1",
                "created_at": "2026-05-08T00:00:00Z",
                "message": "vibelign: checkpoint - CLI daemon test (2026-05-08 00:00)",
                "file_count": 1,
                "total_size_bytes": 1024,
                "pinned": False,
                "trigger": "manual",
                "git_commit_message": None,
                "files": [],
            }
        ],
    }


def _restore_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "result": "restored",
        "checkpoint_id": "cp-cli-1",
    }


def test_vib_history_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    printed: list[str] = []

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.commands.vib_history_cmd.Path.cwd", return_value=tmp_path
    ), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        return_value=_rust_ok(_list_payload()),
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call, patch(
        "vibelign.commands.vib_history_cmd.print", side_effect=lambda value="": printed.append(str(value))
    ):
        run_vib_history(object())

    assert any("CLI daemon test" in line for line in printed)
    assert daemon_call.call_args.args[1]["command"] == "checkpoint_list"
    oneshot_call.assert_not_called()


def test_vib_undo_checkpoint_id_json_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    responses = [_rust_ok(_list_payload()), _rust_ok(_restore_payload())]
    printed: list[str] = []

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.commands.vib_undo_cmd.Path.cwd", return_value=tmp_path
    ), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        side_effect=responses,
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call, patch(
        "vibelign.commands.vib_undo_cmd.print", side_effect=lambda value="": printed.append(str(value))
    ):
        run_vib_undo(Namespace(json=True, checkpoint_id="cp-cli-1", force=True))

    payload = json.loads(printed[-1])
    assert payload["ok"] is True
    assert payload["checkpoint_id"] == "cp-cli-1"
    assert [call.args[1]["command"] for call in daemon_call.call_args_list] == ["checkpoint_list", "checkpoint_restore"]
    oneshot_call.assert_not_called()
