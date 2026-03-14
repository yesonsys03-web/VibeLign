# === ANCHOR: VIB_CHECKPOINT_CMD_START ===
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def _run_git(git_args, cwd):
    return subprocess.run(["git"] + git_args, cwd=cwd, capture_output=True, text=True)


def run_vib_checkpoint(args: Any) -> None:
    root = Path.cwd()
    if not (root / ".git").exists():
        print(
            "Git 저장소가 없습니다. 먼저 `vib init` 또는 `vibeguard init`을 실행하세요."
        )
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if args.message:
        msg = f"vibelign: checkpoint - {' '.join(args.message)} ({timestamp})"
    else:
        msg = f"vibelign: checkpoint ({timestamp})"
    status_result = _run_git(["status", "--porcelain"], cwd=root)
    changed_files = status_result.stdout.strip().splitlines()
    if not changed_files:
        print("변경된 파일이 없습니다. 체크포인트를 건너뜁니다.")
        return
    print(f"저장할 파일 ({len(changed_files)}개):")
    for line in changed_files:
        print(f"  {line}")
    print()
    _ = _run_git(["add", "-A"], cwd=root)
    result = _run_git(["commit", "-m", msg], cwd=root)
    if result.returncode != 0:
        print(f"체크포인트 저장 실패: {result.stderr.strip()}")
        return
    short_hash = (
        _run_git(["rev-parse", "--short", "HEAD"], cwd=root).stdout.strip() or "?"
    )
    print(f"✓ 체크포인트 저장 완료! [{short_hash}]")
    print(f"  메시지: {msg}")
    print("문제가 생기면 `vib undo`로 되돌릴 수 있습니다.")
# === ANCHOR: VIB_CHECKPOINT_CMD_END ===
