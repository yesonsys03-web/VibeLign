# === ANCHOR: VIB_HISTORY_CMD_START ===
import re
from pathlib import Path
from typing import Protocol

from vibelign.core.checkpoint_engine.router import friendly_time, list_checkpoints
from vibelign.core.project_root import resolve_project_root


from vibelign.terminal_render import cli_print

print = cli_print

_TIMESTAMP_PATTERN = re.compile(r"\s*\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)\s*$")


class HistoryCheckpoint(Protocol):
    message: str
    trigger: str | None
    git_commit_message: str | None


def _clean_msg(msg: str, trigger: str | None = None, git_commit_message: str | None = None) -> str:
    if trigger == "post_commit":
        suffix = (git_commit_message or "").strip().splitlines()[0:1]
        if suffix and suffix[0]:
            return f"코드 저장 후 자동 백업 - {suffix[0][:60]}"
        return "코드 저장 후 자동 백업"
    for prefix in ("vibelign: checkpoint - ", "vibelign: checkpoint"):
        if msg.startswith(prefix):
            msg = msg[len(prefix) :]
            break
    msg = _TIMESTAMP_PATTERN.sub("", msg).strip()
    # 훅에서 stdin JSON이 메시지로 들어온 경우 방어
    if msg.startswith("{") or len(msg) > 200:
        return "(자동 저장)"
    return msg or "(메시지 없음)"


def _visible_checkpoints(checkpoints: list[HistoryCheckpoint]) -> list[HistoryCheckpoint]:
    return [cp for cp in checkpoints if cp.trigger != "safe_restore"]


def run_vib_history(_args: object) -> None:
    root = resolve_project_root(Path.cwd())
    checkpoints = _visible_checkpoints(list_checkpoints(root))
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
        msg = _clean_msg(cp.message, cp.trigger, cp.git_commit_message)
        print(f"  [{i + 1:2}]  {time_label:<18}  {msg}{pin}{marker}")
    print()
    print(f"총 {len(checkpoints)}개의 체크포인트")
    print(f"대략 용량: {max(1, round(total_bytes / 1024))}KB")
    print("되돌리려면: vib undo")
    print("새 체크포인트 저장: vib checkpoint '작업 내용'")


# === ANCHOR: VIB_HISTORY_CMD_END ===
