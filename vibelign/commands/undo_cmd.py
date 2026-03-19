# === ANCHOR: UNDO_CMD_START ===
from pathlib import Path

from vibelign.core.local_checkpoints import (
    get_last_restore_error,
    has_changes_since_checkpoint,
    list_checkpoints,
    restore_checkpoint,
)


from vibelign.terminal_render import cli_print

print = cli_print


# === ANCHOR: UNDO_CMD_RUN_UNDO_START ===
def run_undo(args):
    root = Path.cwd()
    checkpoints = list_checkpoints(root)

    if not checkpoints:
        print("저장된 체크포인트가 없습니다.")
        print("먼저 'vib checkpoint'로 현재 상태를 저장하세요.")
        return

    # --list: 체크포인트 목록 출력
    if args.list:
        print("저장된 체크포인트 목록:")
        print()
        for i, cp in enumerate(checkpoints):
            marker = " ← 최근" if i == 0 else ""
            print(f"  [{i + 1}] {cp.created_at:>18}  |  {cp.message}{marker}")
        print()
        print(f"총 {len(checkpoints)}개의 체크포인트가 있습니다.")
        print("되돌리려면: vib undo")
        return
    current = checkpoints[0]
    if has_changes_since_checkpoint(root, current.checkpoint_id):
        print(
            f"현재 작업 내용은 최근 체크포인트 [{current.checkpoint_id[:8]}] 이후에 바뀌었습니다."
        )
        print(f"복구 대상: {current.created_at} - {current.message}")
        print()
        if restore_checkpoint(root, current.checkpoint_id):
            print("✓ 최근 로컬 체크포인트 상태로 복구했습니다!")
        else:
            print(f"되돌리기 실패: {get_last_restore_error()}")
        return
    if len(checkpoints) < 2:
        print("이전 체크포인트가 없습니다.")
        print("현재 상태가 가장 처음 체크포인트입니다.")
        return
    target = checkpoints[1]

    print(
        f"현재 체크포인트:    [{current.checkpoint_id[:8]}] {current.created_at} - {current.message}"
    )
    print(
        f"되돌릴 체크포인트:  [{target.checkpoint_id[:8]}] {target.created_at} - {target.message}"
    )
    print()

    if restore_checkpoint(root, target.checkpoint_id):
        print("✓ 이전 로컬 체크포인트로 되돌렸습니다!")
    else:
        print(f"되돌리기 실패: {get_last_restore_error()}")


# === ANCHOR: UNDO_CMD_RUN_UNDO_END ===
# === ANCHOR: UNDO_CMD_END ===
