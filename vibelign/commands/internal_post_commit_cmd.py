# === ANCHOR: INTERNAL_POST_COMMIT_CMD_START ===
from __future__ import annotations

import os
import sys
from argparse import Namespace
from pathlib import Path

from vibelign.commands.internal_record_commit_cmd import record_commit_message
from vibelign.core.checkpoint_engine.auto_backup import create_post_commit_backup
from vibelign.core.error_log import record_cli_error


def _emit_post_commit_failure(
    project_root: Path, sha: str | None, exc: BaseException, exc_info: tuple
) -> None:
    """자동 백업 실패를 stderr + `.vibelign/logs/cli-error-*.jsonl` 양쪽으로 알린다.

    Why: 자동백업 ON 인 사용자가 Rust 엔진 일시 결함 등으로 백업이 만들어지지
    않으면 `vib history` 가 비어 보일 때 비로소 데이터 부재를 인지한다.
    프로젝트의 통합 로깅(`vibelign/core/error_log.py`) 이 이미 redaction +
    retention(30일) + 회전 + 동시 쓰기 락 을 갖추고 있으므로 그쪽에 위임하고,
    추가로 stderr 에 사람이 읽는 한 줄을 출력해 즉시 가시성을 확보한다.
    git commit 흐름은 절대 막지 않는다.
    """
    summary = f"[vibelign] 자동 백업 실패: {type(exc).__name__}: {exc}"
    sha_label = sha or "unknown"
    argv = ["_internal_post_commit", sha_label]
    try:
        record_cli_error(project_root, exc_info, argv)
    except Exception:
        # 로그 자체가 실패해도 stderr 출력은 계속 시도
        pass
    try:
        sys.stderr.write(summary + "\n")
        sys.stderr.write(
            f"  자세한 내용: {project_root / '.vibelign' / 'logs'} (cli-error-*.jsonl)\n"
        )
    except OSError:
        pass


def run_internal_post_commit(args: Namespace, root: Path | None = None) -> None:
    """Post-commit hook entrypoint; never blocks or fails the user's git commit.

    실패는 stderr + 통합 에러 로그(`vibelign/core/error_log.py`) 로 가시화하되,
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
        _emit_post_commit_failure(project_root, sha, exc, sys.exc_info())
        return
    finally:
        if previous_require_rust is None:
            os.environ.pop("VIBELIGN_REQUIRE_RUST_CHECKPOINT", None)
        else:
            os.environ["VIBELIGN_REQUIRE_RUST_CHECKPOINT"] = previous_require_rust


# === ANCHOR: INTERNAL_POST_COMMIT_CMD_END ===
