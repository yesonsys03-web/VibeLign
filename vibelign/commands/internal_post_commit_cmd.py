# === ANCHOR: INTERNAL_POST_COMMIT_CMD_START ===
from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from vibelign.commands.internal_record_commit_cmd import record_commit_message
from vibelign.core.checkpoint_engine.auto_backup import create_post_commit_backup


def run_internal_post_commit(args: Namespace, root: Path | None = None) -> None:
    """Post-commit hook entrypoint; never blocks or fails the user's git commit."""
    try:
        project_root = root if root is not None else Path.cwd()
        sha = str(args.sha)
        message = sys.stdin.read()
        record_commit_message(project_root, sha, message)
        _ = create_post_commit_backup(project_root, sha, message)
    except Exception:
        return


# === ANCHOR: INTERNAL_POST_COMMIT_CMD_END ===
