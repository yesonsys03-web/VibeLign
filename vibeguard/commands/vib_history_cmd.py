# === ANCHOR: VIB_HISTORY_CMD_START ===
import subprocess
from pathlib import Path
from typing import Any


def _run_git(git_args, cwd):
    return subprocess.run(["git"] + git_args, cwd=cwd, capture_output=True, text=True)


def _clean_msg(msg: str) -> str:
    msg = msg.replace("vibeguard: checkpoint - ", "")
    msg = msg.replace("vibelign: checkpoint - ", "")
    msg = msg.replace("vibeguard: checkpoint", "체크포인트")
    msg = msg.replace("vibelign: checkpoint", "체크포인트")
    msg = msg.replace(
        "vibeguard: 초기 체크포인트 (vibeguard init)", "초기 설정 완료 (vibeguard init)"
    )
    return msg


def run_vib_history(args: Any) -> None:
    root = Path.cwd()
    if not (root / ".git").exists():
        print(
            "Git 저장소가 없습니다. 먼저 `vib init` 또는 `vibeguard init`을 실행하세요."
        )
        return
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
        print("저장된 체크포인트가 없습니다.")
        print("저장하려면: vib checkpoint '작업 내용'")
        return
    checkpoints = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            checkpoints.append(
                {
                    "hash": parts[0][:7],
                    "when": parts[1].strip(),
                    "msg": _clean_msg(parts[2].strip()),
                }
            )
    print("=" * 55)
    print("  VibeLign 체크포인트 이력")
    print("=" * 55)
    print()
    for i, cp in enumerate(checkpoints):
        marker = "  ◀ 최근" if i == 0 else ""
        print(f"  [{i + 1:2}]  {cp['when']:>14}  |  {cp['msg']}{marker}")
    print()
    print(f"총 {len(checkpoints)}개의 체크포인트")
    print("되돌리려면:         vib undo")
    print("목록에서 선택:      vib undo --list")
    print("새 체크포인트 저장: vib checkpoint '작업 내용'")
# === ANCHOR: VIB_HISTORY_CMD_END ===
