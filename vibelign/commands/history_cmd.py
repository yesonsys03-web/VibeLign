# === ANCHOR: HISTORY_CMD_START ===
from pathlib import Path
from typing import Protocol

from vibelign.core.local_checkpoints import list_checkpoints
from vibelign.core.project_root import resolve_project_root


from vibelign.terminal_render import cli_print

print = cli_print


# === ANCHOR: HISTORY_CMD_RUN_HISTORY_START ===
class HistoryArgs(Protocol):
    pass


def run_history(_args: HistoryArgs) -> None:
    root = resolve_project_root(Path.cwd())
    checkpoints = list_checkpoints(root)
    if not checkpoints:
        print("저장된 체크포인트가 없습니다.")
        print()
        print("저장하려면: vib checkpoint '작업 내용'")
        return

    print("=" * 55)
    print("  vib 로컬 체크포인트 이력")
    print("=" * 55)
    print()
    total_bytes = sum(cp.total_size_bytes for cp in checkpoints)

    for i, cp in enumerate(checkpoints):
        marker = "  ◀ 최근" if i == 0 else ""
        pin = " [보호]" if cp.pinned else ""
        print(f"  [{i + 1:2}]  {cp.created_at:>18}  |  {cp.message}{pin}{marker}")

    print()
    print(f"총 {len(checkpoints)}개의 체크포인트")
    print(f"대략 용량: {max(1, round(total_bytes / 1024))}KB")
    print(f"마지막 저장: {checkpoints[0].created_at}")
    print()
    print("되돌리려면:         vib undo")
    print("목록에서 선택:      vib undo --list")
    print("새 체크포인트 저장: vib checkpoint '작업 내용'")


# === ANCHOR: HISTORY_CMD_RUN_HISTORY_END ===
# === ANCHOR: HISTORY_CMD_END ===
