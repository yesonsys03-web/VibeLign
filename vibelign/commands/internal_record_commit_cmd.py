# === ANCHOR: INTERNAL_RECORD_COMMIT_CMD_START ===
from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import record_commit


# === ANCHOR: INTERNAL_RECORD_COMMIT_CMD_RUN_INTERNAL_RECORD_COMMIT_START ===
def run_internal_record_commit(args: Namespace, root: Path | None = None) -> None:
    """post-commit hook internal entrypoint. Reads commit message from stdin and
    records it to recent_events (decisions[] is intentionally untouched)."""
    try:
        project_root = root if root is not None else Path.cwd()
        message = sys.stdin.read()
        record_commit(MetaPaths(project_root).work_memory_path, str(args.sha), message)
    except Exception:
        # post-commit hook must never surface tracebacks to user's git workflow
        return
# === ANCHOR: INTERNAL_RECORD_COMMIT_CMD_RUN_INTERNAL_RECORD_COMMIT_END ===
# === ANCHOR: INTERNAL_RECORD_COMMIT_CMD_END ===
