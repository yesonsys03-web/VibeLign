# === ANCHOR: VIB_UNDO_CMD_START ===
from pathlib import Path
from typing import Any

from vibelign.core.local_checkpoints import (
    friendly_time,
    list_checkpoints,
    restore_checkpoint,
)


from vibelign.terminal_render import cli_print
print = cli_print

def run_vib_undo(args: Any) -> None:
    root = Path.cwd()
    checkpoints = list_checkpoints(root)
    if not checkpoints:
        print("저장된 체크포인트가 없습니다.")
        print("먼저 `vib checkpoint`로 현재 상태를 저장하세요.")
        return

    # 목록 보여주고 선택
    print("어느 시점으로 되돌릴까요?")
    print()
    for i, cp in enumerate(checkpoints):
        marker = "  ← 가장 최근" if i == 0 else ""
        pin = " [보호]" if cp.pinned else ""
        time_label = friendly_time(cp.created_at)
        # 메시지에서 "vibelign: checkpoint - " 접두어 제거해서 깔끔하게 보여줌
        msg = cp.message
        for prefix in ("vibelign: checkpoint - ", "vibelign: checkpoint"):
            if msg.startswith(prefix):
                msg = msg[len(prefix):].strip()
                break
        print(f"  [{i + 1}] {time_label:<18}  {msg}{pin}{marker}")
    print()

    try:
        answer = input("  번호를 입력하세요 (엔터 = 가장 최근): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n취소됐습니다.")
        return

    if not answer:
        idx = 0
    else:
        try:
            idx = int(answer) - 1
        except ValueError:
            print("숫자를 입력해주세요.")
            return
        if idx < 0 or idx >= len(checkpoints):
            print(f"1~{len(checkpoints)} 사이의 번호를 입력해주세요.")
            return

    target = checkpoints[idx]
    time_label = friendly_time(target.created_at)
    msg = target.message
    for prefix in ("vibelign: checkpoint - ", "vibelign: checkpoint"):
        if msg.startswith(prefix):
            msg = msg[len(prefix):].strip()
            break

    print()
    print(f"  되돌릴 시점: [{idx + 1}] {time_label}  {msg}")
    try:
        confirm = input("  정말 되돌릴까요? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n취소됐습니다.")
        return

    if confirm not in ("", "y", "yes"):
        print("취소됐습니다.")
        return

    if restore_checkpoint(root, target.checkpoint_id):
        print(f"✓ [{time_label}] 시점으로 되돌렸습니다!")
    else:
        print("되돌리기 실패: 체크포인트 데이터를 읽지 못했습니다.")


# === ANCHOR: VIB_UNDO_CMD_END ===
