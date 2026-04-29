# === ANCHOR: CHECKPOINT_BRIDGE_START ===
"""Checkpoint Bridge — apply 실행 전 자동 checkpoint 생성."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from vibelign.core.checkpoint_engine.contracts import CheckpointSummary
from vibelign.core.checkpoint_engine.router import create_checkpoint


def create_pre_apply_checkpoint(root: Path) -> Optional[CheckpointSummary]:
    """--apply 실행 직전 자동으로 checkpoint를 생성한다.

    Returns:
        CheckpointSummary if created, None if no changes to snapshot.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"vibelign: checkpoint - apply 전 자동 저장 ({timestamp})"
    return create_checkpoint(root, message)
# === ANCHOR: CHECKPOINT_BRIDGE_END ===
