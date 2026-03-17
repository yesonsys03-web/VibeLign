# === ANCHOR: VIB_HISTORY_CMD_START ===
from pathlib import Path
from typing import Any

from vibelign.core.local_checkpoints import friendly_time, list_checkpoints


from vibelign.terminal_render import cli_print
print = cli_print

def run_vib_history(args: Any) -> None:
    root = Path.cwd()
    checkpoints = list_checkpoints(root)
    if not checkpoints:
        print("저장된 체크포인트가 없습니다.")
        print("저장하려면: vib checkpoint '작업 내용'")
        return
    print("=" * 55)
    print("  VibeLign 로컬 체크포인트 이력")
    print("=" * 55)
    print()
    total_bytes = sum(cp.total_size_bytes for cp in checkpoints)
    for i, cp in enumerate(checkpoints):
        marker = "  ◀ 최근" if i == 0 else ""
        pin = " [보호]" if cp.pinned else ""
        time_label = friendly_time(cp.created_at)
        msg = cp.message
        for prefix in ("vibelign: checkpoint - ", "vibelign: checkpoint"):
            if msg.startswith(prefix):
                msg = msg[len(prefix):].strip()
                break
        print(f"  [{i + 1:2}]  {time_label:<18}  {msg}{pin}{marker}")
    print()
    print(f"총 {len(checkpoints)}개의 체크포인트")
    print(f"대략 용량: {max(1, round(total_bytes / 1024))}KB")
    print("되돌리려면: vib undo")
    print("새 체크포인트 저장: vib checkpoint '작업 내용'")


# === ANCHOR: VIB_HISTORY_CMD_END ===
