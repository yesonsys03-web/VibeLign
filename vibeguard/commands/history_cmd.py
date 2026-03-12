import subprocess
from pathlib import Path


def _run_git(git_args, cwd):
    return subprocess.run(["git"] + git_args, cwd=cwd, capture_output=True, text=True)


def _clean_msg(msg: str) -> str:
    """커밋 메시지에서 vibeguard 접두어를 제거해 읽기 쉽게 만든다."""
    msg = msg.replace("vibeguard: checkpoint - ", "")
    msg = msg.replace("vibeguard: checkpoint", "체크포인트")
    msg = msg.replace("vibeguard: 초기 체크포인트 (vibeguard init)", "초기 설정 완료 (vibeguard init)")
    return msg


def run_history(args):
    root = Path.cwd()

    if not (root / ".git").exists():
        print("Git 저장소가 없습니다. 먼저 'vibeguard init'을 실행하세요.")
        return

    # vibeguard 체크포인트 커밋만 가져오기
    result = _run_git(
        ["log", "--grep=vibeguard:", "--format=%H|%ar|%s"],
        cwd=root,
    )

    if result.returncode != 0 or not result.stdout.strip():
        print("저장된 체크포인트가 없습니다.")
        print()
        print("저장하려면: vibeguard checkpoint '작업 내용'")
        return

    lines = result.stdout.strip().splitlines()
    checkpoints = []
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) == 3:
            checkpoints.append({
                "hash": parts[0][:7],
                "when": parts[1].strip(),
                "msg": _clean_msg(parts[2].strip()),
            })

    print("=" * 55)
    print("  VibeGuard 체크포인트 이력")
    print("=" * 55)
    print()

    for i, cp in enumerate(checkpoints):
        marker = "  ◀ 최근" if i == 0 else ""
        print(f"  [{i + 1:2}]  {cp['when']:>14}  |  {cp['msg']}{marker}")

    print()
    print(f"총 {len(checkpoints)}개의 체크포인트")
    print(f"마지막 저장: {checkpoints[0]['when']}")
    print()
    print("되돌리려면:         vibeguard undo")
    print("목록에서 선택:      vibeguard undo --list")
    print("새 체크포인트 저장: vibeguard checkpoint '작업 내용'")
