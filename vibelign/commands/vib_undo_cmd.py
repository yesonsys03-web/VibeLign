# === ANCHOR: VIB_UNDO_CMD_START ===
import re
from pathlib import Path
from typing import Any

from vibelign.core.local_checkpoints import (
    friendly_time,
    list_checkpoints,
    restore_checkpoint,
)


from vibelign.terminal_render import cli_print
print = cli_print

# "vibelign: checkpoint - 시작 (2026-03-17 16:52)" → "시작"
_TIMESTAMP_PATTERN = re.compile(r"\s*\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)\s*$")

def _clean_msg(msg: str) -> str:
    """메시지에서 vibelign 접두어와 날짜 접미어를 제거."""
    for prefix in ("vibelign: checkpoint - ", "vibelign: checkpoint"):
        if msg.startswith(prefix):
            msg = msg[len(prefix):]
            break
    msg = _TIMESTAMP_PATTERN.sub("", msg).strip()
    # 훅에서 stdin JSON이 메시지로 들어온 경우 방어
    if msg.startswith("{") or len(msg) > 200:
        return "(자동 저장)"
    return msg or "(메시지 없음)"


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
        msg = _clean_msg(cp.message)
        print(f"  [{i + 1}] {time_label:<18}  {msg}{pin}{marker}")
    print(f"  [0] 취소")
    print()

    try:
        answer = input("  번호를 입력하세요 (엔터 = 가장 최근): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n취소됐습니다.")
        return

    if not answer:
        idx = 0
    elif answer in ("0", "q", "n", "취소"):
        print("취소됐습니다.")
        return
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
    msg = _clean_msg(target.message)

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
