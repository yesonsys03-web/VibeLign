# === ANCHOR: VIB_UNDO_CMD_START ===
import subprocess
from pathlib import Path
from typing import Any, List, Dict


def _run_git(git_args, cwd):
    return subprocess.run(["git"] + git_args, cwd=cwd, capture_output=True, text=True)


def _get_checkpoints(root: Path) -> List[Dict[str, str]]:
    result = _run_git(
        [
            "log",
            "--grep=vibeguard:|vibelign:",
            "--extended-regexp",
            "--format=%H|%ar|%s",
        ],
        cwd=root,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    checkpoints = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            checkpoints.append({"hash": parts[0], "when": parts[1], "msg": parts[2]})
    return checkpoints


def run_vib_undo(args: Any) -> None:
    root = Path.cwd()
    if not (root / ".git").exists():
        print(
            "Git 저장소가 없습니다. 먼저 `vib init` 또는 `vibeguard init`을 실행하세요."
        )
        return
    checkpoints = _get_checkpoints(root)
    if not checkpoints:
        print("저장된 체크포인트가 없습니다.")
        print("먼저 `vib checkpoint`로 현재 상태를 저장하세요.")
        return
    if args.list:
        print("저장된 체크포인트 목록:")
        print()
        for i, cp in enumerate(checkpoints):
            marker = " ← 최근" if i == 0 else ""
            print(f"  [{i + 1}] {cp['when']:>15}  |  {cp['msg']}{marker}")
        print()
        print(f"총 {len(checkpoints)}개의 체크포인트가 있습니다.")
        print("되돌리려면: vib undo")
        return
    status_result = _run_git(["status", "--porcelain"], cwd=root)
    has_uncommitted = bool(status_result.stdout.strip())
    if has_uncommitted:
        target = checkpoints[0]
        changed_files = status_result.stdout.strip().splitlines()
        print(f"마지막 체크포인트 이후 변경된 파일 ({len(changed_files)}개):")
        for line in changed_files:
            print(f"  {line}")
        print()
        print(f"되돌릴 체크포인트: [{target['hash'][:7]}] {target['msg']}")
        print()
        result = _run_git(["reset", "--hard", "HEAD"], cwd=root)
        if result.returncode == 0:
            print("✓ 되돌리기 완료!")
            print("  새 파일은 수동으로 삭제해야 할 수 있습니다.")
        else:
            print(f"되돌리기 실패: {result.stderr.strip()}")
        return
    if len(checkpoints) < 2:
        print("이전 체크포인트가 없습니다.")
        print("현재 상태가 가장 처음 체크포인트입니다.")
        return
    current = checkpoints[0]
    target = checkpoints[1]
    print(
        f"현재 체크포인트:    [{current['hash'][:7]}] {current['when']} - {current['msg']}"
    )
    print(
        f"되돌릴 체크포인트:  [{target['hash'][:7]}] {target['when']} - {target['msg']}"
    )
    print()
    result = _run_git(["reset", "--hard", target["hash"]], cwd=root)
    if result.returncode == 0:
        print("✓ 이전 체크포인트로 되돌렸습니다!")
    else:
        print(f"되돌리기 실패: {result.stderr.strip()}")
# === ANCHOR: VIB_UNDO_CMD_END ===
