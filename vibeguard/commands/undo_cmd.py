import subprocess
from pathlib import Path


def _run_git(git_args, cwd):
    return subprocess.run(["git"] + git_args, cwd=cwd, capture_output=True, text=True)


def _get_checkpoints(root):
    """vibeguard checkpoint 커밋 목록 반환 (최신순)"""
    result = _run_git(
        ["log", "--grep=vibeguard:", "--format=%H|%ar|%s"],
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


def run_undo(args):
    root = Path.cwd()

    # Git 저장소 확인
    if not (root / ".git").exists():
        print("Git 저장소가 없습니다. 먼저 'vibeguard init'을 실행하세요.")
        return

    checkpoints = _get_checkpoints(root)

    if not checkpoints:
        print("저장된 체크포인트가 없습니다.")
        print("먼저 'vibeguard checkpoint'로 현재 상태를 저장하세요.")
        return

    # --list: 체크포인트 목록 출력
    if args.list:
        print("저장된 체크포인트 목록:")
        print()
        for i, cp in enumerate(checkpoints):
            marker = " ← 최근" if i == 0 else ""
            print(f"  [{i + 1}] {cp['when']:>15}  |  {cp['msg']}{marker}")
        print()
        print(f"총 {len(checkpoints)}개의 체크포인트가 있습니다.")
        print("되돌리려면: vibeguard undo")
        return

    # 미저장 변경사항 확인
    status_result = _run_git(["status", "--porcelain"], cwd=root)
    has_uncommitted = bool(status_result.stdout.strip())

    if has_uncommitted:
        # 케이스 1: 저장 안 된 변경사항이 있음 → 마지막 체크포인트로 복구
        target = checkpoints[0]
        changed_files = status_result.stdout.strip().splitlines()

        print(f"마지막 체크포인트 이후 변경된 파일 ({len(changed_files)}개):")
        for line in changed_files:
            print(f"  {line}")
        print()
        print(f"되돌릴 체크포인트: [{target['hash'][:7]}] {target['msg']}")
        print()

        # 트래킹된 파일만 복구 (git restore .)
        result = _run_git(["restore", "."], cwd=root)
        if result.returncode == 0:
            print("✓ 되돌리기 완료!")
            print()
            print("  주의: 체크포인트 이후 새로 추가된 파일은 그대로 남아 있습니다.")
            print("  새 파일도 지우려면 수동으로 삭제하세요.")
        else:
            print(f"되돌리기 실패: {result.stderr.strip()}")

    else:
        # 케이스 2: 깨끗한 상태 → 이전 체크포인트로 이동
        if len(checkpoints) < 2:
            print("이전 체크포인트가 없습니다.")
            print("현재 상태가 가장 처음 체크포인트입니다.")
            return

        current = checkpoints[0]
        target = checkpoints[1]

        print(f"현재 체크포인트:    [{current['hash'][:7]}] {current['when']} - {current['msg']}")
        print(f"되돌릴 체크포인트:  [{target['hash'][:7]}] {target['when']} - {target['msg']}")
        print()
        print("주의: 현재 체크포인트 이후의 변경사항이 모두 사라집니다.")
        print()

        result = _run_git(["reset", "--hard", target["hash"]], cwd=root)
        if result.returncode == 0:
            print("✓ 이전 체크포인트로 되돌렸습니다!")
        else:
            print(f"되돌리기 실패: {result.stderr.strip()}")
