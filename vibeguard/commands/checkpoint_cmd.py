import subprocess
from datetime import datetime
from pathlib import Path


def _run_git(git_args, cwd):
    return subprocess.run(["git"] + git_args, cwd=cwd, capture_output=True, text=True)


def run_checkpoint(args):
    root = Path.cwd()

    # Git 저장소 확인
    if not (root / ".git").exists():
        print("Git 저장소가 없습니다. 먼저 'vibeguard init'을 실행하세요.")
        return

    # 커밋 메시지 구성
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if args.message:
        msg = f"vibeguard: checkpoint - {' '.join(args.message)} ({timestamp})"
    else:
        msg = f"vibeguard: checkpoint ({timestamp})"

    # 변경된 파일 목록 미리 보기
    status_result = _run_git(["status", "--porcelain"], cwd=root)
    changed_files = status_result.stdout.strip().splitlines()

    if not changed_files:
        print("변경된 파일이 없습니다. 체크포인트를 생략합니다.")
        print("파일을 수정하거나 추가한 뒤 다시 실행하세요.")
        return

    print(f"저장할 파일 ({len(changed_files)}개):")
    for line in changed_files:
        print(f"  {line}")
    print()

    # git add -A + commit
    _run_git(["add", "-A"], cwd=root)
    result = _run_git(["commit", "-m", msg], cwd=root)

    if result.returncode == 0:
        # 짧은 해시 가져오기
        hash_result = _run_git(["rev-parse", "--short", "HEAD"], cwd=root)
        short_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "?"

        # 전체 vibeguard 체크포인트 개수
        log_result = _run_git(
            ["log", "--oneline", "--grep=vibeguard: checkpoint"],
            cwd=root,
        )
        count = len(log_result.stdout.strip().splitlines()) if log_result.returncode == 0 else 1

        print(f"✓ 체크포인트 저장 완료! [{short_hash}]")
        print(f"  메시지: {msg}")
        print(f"  총 체크포인트: {count}개")
        print()
        print("문제가 생기면 'vibeguard undo'로 되돌릴 수 있습니다.")
    else:
        stderr = result.stderr.strip()
        print(f"체크포인트 저장 실패: {stderr}")
