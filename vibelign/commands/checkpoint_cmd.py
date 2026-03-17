# === ANCHOR: CHECKPOINT_CMD_START ===
from datetime import datetime
from pathlib import Path

from vibelign.core.local_checkpoints import create_checkpoint



from vibelign.terminal_render import cli_print
print = cli_print

# === ANCHOR: CHECKPOINT_CMD_RUN_CHECKPOINT_START ===
def run_checkpoint(args):
    root = Path.cwd()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if args.message:
        msg = f"vib: checkpoint - {' '.join(args.message)} ({timestamp})"
    else:
        msg = f"vib: checkpoint ({timestamp})"
    summary = create_checkpoint(root, msg)
    if summary is None:
        print("변경된 파일이 없습니다. 체크포인트를 생략합니다.")
        print("파일을 수정하거나 추가한 뒤 다시 실행하세요.")
        return
    print(f"✓ 로컬 체크포인트 저장 완료! [{summary.checkpoint_id[:8]}]")
    print(f"  메시지: {summary.message}")
    print(f"  파일 수: {summary.file_count}개")
    if summary.pruned_count:
        freed_kb = max(1, round(summary.pruned_bytes / 1024))
        print(
            f"  오래된 체크포인트 {summary.pruned_count}개를 정리했고, 약 {freed_kb}KB를 비웠어요."
        )
    print()
    print("문제가 생기면 'vib undo'로 되돌릴 수 있습니다.")
# === ANCHOR: CHECKPOINT_CMD_RUN_CHECKPOINT_END ===
# === ANCHOR: CHECKPOINT_CMD_END ===
