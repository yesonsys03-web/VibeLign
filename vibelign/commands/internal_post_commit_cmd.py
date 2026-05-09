# === ANCHOR: INTERNAL_POST_COMMIT_CMD_START ===
from __future__ import annotations

import os
import sys
import traceback
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

from vibelign.commands.internal_record_commit_cmd import record_commit_message
from vibelign.core.checkpoint_engine.auto_backup import create_post_commit_backup


_POST_COMMIT_LOG_REL = Path(".vibelign") / "logs" / "post_commit_errors.log"


def _record_post_commit_error(
    project_root: Path, sha: str | None, exc: BaseException
) -> None:
    """Persist + emit visibility for post-commit failures.

    Why: 자동백업 ON 인 사용자가 Rust 엔진 일시 결함 등으로 백업이 만들어지지
    않았을 때 조용히 넘어가면 데이터 부재를 인지하지 못한다 (`vib history` 비어
    보임). 로그 파일 + stderr 양쪽으로 가시성을 확보하되 git commit 자체는
    절대 실패시키지 않는다.
    """
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sha_label = sha or "unknown"
    summary = f"[vibelign] 자동 백업 실패: {type(exc).__name__}: {exc}"
    try:
        log_path = project_root / _POST_COMMIT_LOG_REL
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} sha={sha_label} {type(exc).__name__}: {exc}\n")
            handle.write(traceback.format_exc())
            handle.write("\n")
    except OSError:
        # 로그 쓰기 자체가 실패해도 stderr 출력은 시도한다.
        pass
    try:
        sys.stderr.write(summary + "\n")
        sys.stderr.write(
            f"  자세한 내용: {project_root / _POST_COMMIT_LOG_REL}\n"
        )
    except OSError:
        pass


def run_internal_post_commit(args: Namespace, root: Path | None = None) -> None:
    """Post-commit hook entrypoint; never blocks or fails the user's git commit.

    실패는 stderr + `.vibelign/logs/post_commit_errors.log` 로 가시화하되,
    예외를 git 으로 전파하지는 않는다.
    """
    project_root = root if root is not None else Path.cwd()
    sha: str | None = None
    previous_require_rust = os.environ.get("VIBELIGN_REQUIRE_RUST_CHECKPOINT")
    try:
        sha = str(args.sha)
        message = sys.stdin.read()
        record_commit_message(project_root, sha, message)
        os.environ["VIBELIGN_REQUIRE_RUST_CHECKPOINT"] = "1"
        _ = create_post_commit_backup(project_root, sha, message)
    except Exception as exc:
        _record_post_commit_error(project_root, sha, exc)
        return
    finally:
        if previous_require_rust is None:
            os.environ.pop("VIBELIGN_REQUIRE_RUST_CHECKPOINT", None)
        else:
            os.environ["VIBELIGN_REQUIRE_RUST_CHECKPOINT"] = previous_require_rust


# === ANCHOR: INTERNAL_POST_COMMIT_CMD_END ===
