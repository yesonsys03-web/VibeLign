# === ANCHOR: VIB_UNDO_CMD_START ===
from argparse import Namespace
import json
import re
from pathlib import Path
from typing import Protocol

from vibelign.core.checkpoint_engine.router import (
    friendly_time,
    get_last_restore_error,
    list_checkpoints,
    restore_checkpoint,
)
from vibelign.core.project_root import resolve_project_root


from vibelign.terminal_render import cli_print

print = cli_print

# "vibelign: checkpoint - 시작 (2026-03-17 16:52)" → "시작"
_TIMESTAMP_PATTERN = re.compile(r"\s*\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)\s*$")


class UndoCheckpoint(Protocol):
    message: str
    trigger: str | None
    git_commit_message: str | None


def _clean_msg(msg: str, trigger: str | None = None, git_commit_message: str | None = None) -> str:
    """메시지에서 vibelign 접두어와 날짜 접미어를 제거."""
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
    if msg.startswith("{") or len(msg) > 200:
        return "(자동 저장)"
    return msg or "(메시지 없음)"


def _visible_checkpoints(checkpoints: list[UndoCheckpoint]) -> list[UndoCheckpoint]:
    return [cp for cp in checkpoints if cp.trigger != "safe_restore"]


def run_vib_undo(args: Namespace) -> None:
    root = resolve_project_root(Path.cwd())
    as_json = bool(getattr(args, "json", False))
    checkpoint_id_value = getattr(args, "checkpoint_id", None)
    checkpoint_id = (
        checkpoint_id_value if isinstance(checkpoint_id_value, str) else None
    )
    force = bool(getattr(args, "force", False))

    checkpoints = _visible_checkpoints(list_checkpoints(root))
    if not checkpoints:
        if as_json:
            print(
                json.dumps({"ok": False, "error": "no_checkpoints"}, ensure_ascii=False)
            )
        else:
            print("저장된 체크포인트가 없습니다.")
            print("먼저 `vib checkpoint`로 현재 상태를 저장하세요.")
        return

    # --checkpoint-id 지정 시 대화형 선택 생략
    if checkpoint_id:
        matched = next(
            (cp for cp in checkpoints if cp.checkpoint_id == checkpoint_id), None
        )
        if matched is None:
            if as_json:
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "error": "checkpoint_not_found",
                            "checkpoint_id": checkpoint_id,
                        },
                        ensure_ascii=False,
                    )
                )
            else:
                print(f"checkpoint_id '{checkpoint_id}'를 찾을 수 없습니다.")
            return
        target = matched
    else:
        # 대화형 목록 선택
        print("어느 시점으로 되돌릴까요?")
        print()
        for i, cp in enumerate(checkpoints):
            marker = "  ← 가장 최근" if i == 0 else ""
            pin = " [보호]" if cp.pinned else ""
            time_label = friendly_time(cp.created_at)
            msg = _clean_msg(cp.message, cp.trigger, cp.git_commit_message)
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
    msg = _clean_msg(target.message, target.trigger, target.git_commit_message)

    # --force 없고 대화형 선택인 경우 확인 프롬프트
    if not force and not checkpoint_id:
        print()
        print(f"  되돌릴 시점: {time_label}  {msg}")
        try:
            confirm = input("  정말 되돌릴까요? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n취소됐습니다.")
            return
        if confirm not in ("", "y", "yes"):
            print("취소됐습니다.")
            return

    if restore_checkpoint(root, target.checkpoint_id):
        if as_json:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "checkpoint_id": target.checkpoint_id,
                        "message": msg,
                        "restored_at": time_label,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"✓ [{time_label}] 시점으로 되돌렸습니다!")
    else:
        error = get_last_restore_error()
        if as_json:
            print(
                json.dumps(
                    {"ok": False, "error": error or "restore_failed"},
                    ensure_ascii=False,
                )
            )
        else:
            print(f"되돌리기 실패: {error}")


# === ANCHOR: VIB_UNDO_CMD_END ===
