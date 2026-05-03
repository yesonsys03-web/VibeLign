import importlib
from pathlib import Path
from typing import Protocol, cast
from unittest.mock import patch

from vibelign.core.local_checkpoints import CheckpointSummary


class SandwichResult(Protocol):
    ok: bool
    before_checkpoint_id: str
    safety_checkpoint_id: str
    file_count: int
    paths: list[str]
    error: str | None
    metadata_only: bool


class CreateRecoverySandwichCheckpoint(Protocol):
    def __call__(self, root: Path, *, before_checkpoint_id: str, paths: list[str]) -> SandwichResult: ...


create_recovery_sandwich_checkpoint = cast(
    CreateRecoverySandwichCheckpoint,
    getattr(importlib.import_module("vibelign.core.recovery.sandwich"), "create_recovery_sandwich_checkpoint"),
)


def test_create_recovery_sandwich_checkpoint_uses_public_checkpoint_api(tmp_path: Path) -> None:
    summary = CheckpointSummary("ckpt_safety", "2026-05-03T10:00:00Z", "safety", 2)

    with patch("vibelign.core.checkpoint_engine.router.create_checkpoint", return_value=summary) as create_checkpoint:
        result = create_recovery_sandwich_checkpoint(
            tmp_path,
            before_checkpoint_id="ckpt_before",
            paths=["src/app.py", "src/other.py"],
        )

    create_checkpoint.assert_called_once_with(
        tmp_path,
        "vibelign: recovery safety checkpoint before apply from ckpt_before",
        trigger="recovery_sandwich",
    )
    assert result.ok is True
    assert result.before_checkpoint_id == "ckpt_before"
    assert result.safety_checkpoint_id == "ckpt_safety"
    assert result.file_count == 2
    assert result.paths == ["src/app.py", "src/other.py"]
    assert result.error is None
    assert result.metadata_only is False


def test_create_recovery_sandwich_checkpoint_reports_no_change_block(tmp_path: Path) -> None:
    with patch("vibelign.core.checkpoint_engine.router.create_checkpoint", return_value=None):
        result = create_recovery_sandwich_checkpoint(
            tmp_path,
            before_checkpoint_id="ckpt_before",
            paths=["src/app.py"],
        )

    assert result.ok is False
    assert result.before_checkpoint_id == "ckpt_before"
    assert result.safety_checkpoint_id == ""
    assert result.file_count == 0
    assert result.paths == ["src/app.py"]
    assert result.error == "no changes available for recovery safety checkpoint"
    assert result.metadata_only is False


def test_create_recovery_sandwich_checkpoint_requires_before_checkpoint_id(tmp_path: Path) -> None:
    result = create_recovery_sandwich_checkpoint(tmp_path, before_checkpoint_id="", paths=[])

    assert result.ok is False
    assert result.error == "before_checkpoint_id is required before recovery apply"
    assert result.safety_checkpoint_id == ""
