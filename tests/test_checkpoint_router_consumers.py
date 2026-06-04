from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.action_engine.executors.checkpoint_bridge import create_pre_apply_checkpoint
from vibelign.commands.vib_backup_db_maintenance_cmd import run_vib_backup_db_maintenance
from vibelign.commands.vib_checkpoint_cmd import create_for_cli as vib_checkpoint_create_for_cli
from vibelign.commands.vib_transfer_cmd import get_recent_checkpoints
from vibelign.core.checkpoint_engine.auto_backup import create_post_commit_backup
from vibelign.core.checkpoint_engine.rust_engine import RustEngineResult
from vibelign.core.hook_setup import setup_hook_if_needed
from vibelign.core.recovery.apply import _restore_files as recovery_restore_files
from vibelign.core.recovery.sandwich import create_recovery_sandwich_checkpoint
from vibelign.core.recovery.signals import _iter_auto_backup_checkpoints


def _rust_ok(payload: dict[str, object]) -> RustEngineResult:
    return RustEngineResult(ok=True, payload=payload)


def _created_payload(message: str, *, trigger: str | None = None) -> dict[str, object]:
    return {
        "status": "ok",
        "result": "created",
        "checkpoint_id": "cp-daemon-1",
        "created_at": "2026-05-08T00:00:00Z",
        "message": message,
        "file_count": 1,
        "total_size_bytes": 12,
        "pinned": False,
        "trigger": trigger,
        "git_commit_message": "feat: daemon consumer matrix",
        "files": [],
    }


def _pruned_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "result": "pruned",
        "pruned_count": 0,
        "pruned_bytes": 0,
    }


def _list_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "result": "listed",
        "checkpoints": [
            {
                "checkpoint_id": "cp-daemon-list",
                "created_at": "2026-05-08T00:00:00Z",
                "message": "vibelign: auto backup after commit abc1234",
                "file_count": 2,
                "total_size_bytes": 34,
                "pinned": False,
                "trigger": "post_commit",
                "git_commit_message": "feat: daemon consumer matrix",
                "files": [],
            }
        ],
    }


def test_post_commit_auto_backup_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    responses = [
        _rust_ok(_created_payload("vibelign: auto backup after commit abc1234", trigger="post_commit")),
        _rust_ok(_pruned_payload()),
    ]

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        side_effect=responses,
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call:
        result = create_post_commit_backup(tmp_path, "abc123456789", "feat: daemon consumer matrix")

    assert result.status == "created"
    assert result.checkpoint_id == "cp-daemon-1"
    assert [call.args[1]["command"] for call in daemon_call.call_args_list] == ["checkpoint_create", "checkpoint_prune"]
    oneshot_call.assert_not_called()


def test_action_engine_checkpoint_bridge_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    responses = [
        _rust_ok(_created_payload("vibelign: checkpoint - apply 전 자동 저장")),
        _rust_ok(_pruned_payload()),
    ]

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        side_effect=responses,
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call:
        summary = create_pre_apply_checkpoint(tmp_path)

    assert summary is not None
    assert summary.checkpoint_id == "cp-daemon-1"
    assert daemon_call.call_args_list[0].args[1]["command"] == "checkpoint_create"
    oneshot_call.assert_not_called()


def test_transfer_recent_checkpoints_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        return_value=_rust_ok(_list_payload()),
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call:
        checkpoints = get_recent_checkpoints(tmp_path, n=1)

    assert len(checkpoints) == 1
    assert checkpoints[0]["id"] == "cp-daemon-list"
    assert checkpoints[0]["message"] == "vibelign: auto backup after commit abc1234"
    assert checkpoints[0]["time"]
    assert daemon_call.call_args.args[1]["command"] == "checkpoint_list"
    oneshot_call.assert_not_called()


def test_recovery_auto_backup_signal_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        return_value=_rust_ok(_list_payload()),
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call:
        rows = _iter_auto_backup_checkpoints(tmp_path)

    assert rows == [
        {
            "checkpoint_id": "cp-daemon-list",
            "created_at": "2026-05-08T00:00:00Z",
            "message": "vibelign: auto backup after commit abc1234",
            "commit_hash": "abc1234",
            "commit_message": "feat: daemon consumer matrix",
            "preview_available": True,
            "files": [],
        }
    ]
    assert daemon_call.call_args.args[1]["command"] == "checkpoint_list"
    oneshot_call.assert_not_called()


def test_hook_setup_initial_checkpoint_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    responses = [
        _rust_ok({"status": "ok", "result": "listed", "checkpoints": []}),
        _rust_ok(_created_payload("vibelign: checkpoint - vib start 초기 저장")),
        _rust_ok(_pruned_payload()),
    ]

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        side_effect=responses,
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call, patch(
        "vibelign.core.hook_setup.detect_tool", return_value="none"
    ):
        result = setup_hook_if_needed(tmp_path)

    assert result is None
    assert [call.args[1]["command"] for call in daemon_call.call_args_list] == ["checkpoint_list", "checkpoint_create", "checkpoint_prune"]
    oneshot_call.assert_not_called()


def test_vib_checkpoint_create_for_cli_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    responses = [
        _rust_ok(_created_payload("vibelign: cli manual checkpoint")),
        _rust_ok(_pruned_payload()),
    ]

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        side_effect=responses,
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call:
        summary, error = vib_checkpoint_create_for_cli(tmp_path, "vibelign: cli manual checkpoint")

    assert error is None
    assert summary is not None
    assert summary.checkpoint_id == "cp-daemon-1"
    assert [call.args[1]["command"] for call in daemon_call.call_args_list] == ["checkpoint_create", "checkpoint_prune"]
    oneshot_call.assert_not_called()


def test_recovery_sandwich_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    responses = [
        _rust_ok(_created_payload(
            "vibelign: recovery safety checkpoint before apply from cp-before",
            trigger="recovery_sandwich",
        )),
        _rust_ok(_pruned_payload()),
    ]

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        side_effect=responses,
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call:
        result = create_recovery_sandwich_checkpoint(
            tmp_path,
            before_checkpoint_id="cp-before",
            paths=["src/app.py"],
        )

    assert result.ok is True
    assert result.safety_checkpoint_id == "cp-daemon-1"
    assert [call.args[1]["command"] for call in daemon_call.call_args_list] == ["checkpoint_create", "checkpoint_prune"]
    oneshot_call.assert_not_called()


def test_recovery_apply_restore_files_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    restore_payload: dict[str, object] = {
        "status": "ok",
        "result": "restored_files",
        "restored_count": 2,
    }

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        return_value=_rust_ok(restore_payload),
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call:
        restored = recovery_restore_files(tmp_path, "cp-target", ["src/app.py", "src/util.py"])

    assert restored == 2
    assert daemon_call.call_args.args[1]["command"] == "checkpoint_restore_files_safe"
    oneshot_call.assert_not_called()


def test_vib_backup_db_maintenance_uses_daemon_router_when_opted_in(tmp_path: Path) -> None:
    """vib backup-db maintenance --json 가 daemon 경로로 라우팅되고 결과가 동일한지 검증.

    Why: plan §5.4 에 따라 retention/maintenance 류 명령은 fallback 시 응답 shape parity 가 깨질
    위험이 있어 매트릭스 항목으로 고정. daemon ON 상태에서 1-shot 호출이 일어나면 안 됨.
    """
    maintenance_payload: dict[str, object] = {
        "status": "ok",
        "result": "backup_db_maintenance",
        "applied": False,
        "actions": [],
        "summary": {"orphan_objects": 0, "orphan_bytes": 0},
    }
    printed: list[str] = []

    with patch.dict("os.environ", {"VIBELIGN_ENGINE_DAEMON": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.call_rust_engine_daemon",
        return_value=_rust_ok(maintenance_payload),
    ) as daemon_call, patch("vibelign.core.checkpoint_engine.rust_engine.call_rust_engine") as oneshot_call, patch(
        "vibelign.commands.vib_backup_db_maintenance_cmd.resolve_project_root", return_value=tmp_path
    ), patch(
        "vibelign.commands.vib_backup_db_maintenance_cmd.print",
        side_effect=lambda value="": printed.append(str(value)),
    ):
        exit_code = run_vib_backup_db_maintenance(Namespace(root=str(tmp_path), apply=False, json=True))

    assert exit_code == 0
    payload = json.loads(printed[-1])
    assert payload["ok"] is True
    assert payload["result"] == "backup_db_maintenance"
    assert payload["applied"] is False
    assert daemon_call.call_args.args[1]["command"] == "backup_db_maintenance"
    oneshot_call.assert_not_called()
