# === ANCHOR: RECOVERY_SANDWICH_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RecoverySandwichCheckpointResult:
    ok: bool
    before_checkpoint_id: str
    safety_checkpoint_id: str
    file_count: int
    paths: list[str] = field(default_factory=list)
    error: str | None = None
    metadata_only: bool = False


def create_recovery_sandwich_checkpoint(
    root: Path,
    *,
    before_checkpoint_id: str,
    paths: list[str],
) -> RecoverySandwichCheckpointResult:
    checkpoint_id = before_checkpoint_id.strip()
    normalized_paths = [path.replace("\\", "/") for path in paths]
    if not checkpoint_id:
        return RecoverySandwichCheckpointResult(
            ok=False,
            before_checkpoint_id="",
            safety_checkpoint_id="",
            file_count=0,
            paths=normalized_paths,
            error="before_checkpoint_id is required before recovery apply",
            metadata_only=False,
        )

    from vibelign.core.checkpoint_engine.router import create_checkpoint

    summary = create_checkpoint(
        root,
        f"vibelign: recovery safety checkpoint before apply from {checkpoint_id}",
        trigger="recovery_sandwich",
    )
    if summary is None:
        return RecoverySandwichCheckpointResult(
            ok=False,
            before_checkpoint_id=checkpoint_id,
            safety_checkpoint_id="",
            file_count=0,
            paths=normalized_paths,
            error="no changes available for recovery safety checkpoint",
            metadata_only=False,
        )
    return RecoverySandwichCheckpointResult(
        ok=True,
        before_checkpoint_id=checkpoint_id,
        safety_checkpoint_id=summary.checkpoint_id,
        file_count=summary.file_count,
        paths=normalized_paths,
        error=None,
        metadata_only=False,
    )
# === ANCHOR: RECOVERY_SANDWICH_END ===
