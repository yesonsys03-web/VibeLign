# === ANCHOR: VIB_CHECKPOINT_CMD_START ===
from datetime import datetime
from pathlib import Path
from typing import Any

from vibelign.core.local_checkpoints import create_checkpoint
from vibelign.core.meta_paths import MetaPaths


from vibelign.terminal_render import cli_print
print = cli_print

def run_vib_checkpoint(args: Any) -> None:
    root = Path.cwd()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if args.message:
        user_msg = ' '.join(args.message).strip()
    else:
        # 메시지 없으면 입력 유도
        print('💡 메시지를 넣으면 나중에 어느 시점인지 찾기 쉬워요!')
        print('   예: "로그인 기능 추가 전"  /  "결제 모듈 연동 완료"')
        try:
            user_msg = input('   메시지 입력 (엔터 = 건너뜀): ').strip()
        except (EOFError, KeyboardInterrupt):
            user_msg = ""

    if user_msg:
        msg = f"vibelign: checkpoint - {user_msg} ({timestamp})"
    else:
        msg = f"vibelign: checkpoint ({timestamp})"

    summary = create_checkpoint(root, msg)
    if summary is None:
        print("변경된 파일이 없습니다. 체크포인트를 건너뜁니다.")
        return
    meta = MetaPaths(root)
    display_msg = user_msg if user_msg else "(메시지 없음)"
    print(f"✓ 체크포인트 저장 완료!")
    print(f"  메시지: {display_msg}")
    print(f"  파일 수: {summary.file_count}개")
    if summary.pruned_count:
        freed_kb = max(1, round(summary.pruned_bytes / 1024))
        print(f"  오래된 체크포인트 {summary.pruned_count}개를 정리했고, 약 {freed_kb}KB를 비웠어요.")
    print("문제가 생기면 `vib undo`로 되돌릴 수 있습니다.")


# === ANCHOR: VIB_CHECKPOINT_CMD_END ===
