# === ANCHOR: VIB_CLI_START ===
import argparse
import importlib
import sys

from .commands.vib_anchor_cmd import run_vib_anchor
from .commands.vib_checkpoint_cmd import run_vib_checkpoint
from .commands.vib_doctor_cmd import run_vib_doctor
from .commands.vib_explain_cmd import run_vib_explain
from .commands.vib_history_cmd import run_vib_history
from .commands.vib_init_cmd import run_vib_init_cli
from .commands.vib_patch_cmd import run_vib_patch
from .commands.vib_start_cmd import run_vib_start
from .commands.vib_undo_cmd import run_vib_undo
from vibelign.commands.ask_cmd import run_ask
from vibelign.commands.config_cmd import run_config
from vibelign.commands.export_cmd import run_export
from vibelign.commands.protect_cmd import run_protect
from vibelign.commands.watch_cmd import run_watch_cmd
from vibelign.terminal_render import print_cli_help


class RichArgumentParser(argparse.ArgumentParser):
    def _print_message(self, message, file=None):
        if not message:
            return
        if file not in (None, sys.stdout):
            file.write(message)
            return
        print_cli_help(str(message))


def build_parser():
    run_vib_guard = importlib.import_module(
        "vibelign.commands.vib_guard_cmd"
    ).run_vib_guard
    parser = RichArgumentParser(
        prog="vib",
        description="VibeLign CLI (VibeLign와 호환되는 새 진입점)",
    )
    sub = parser.add_subparsers(
        dest="command", required=True, parser_class=RichArgumentParser
    )

    p = sub.add_parser("init", help="프로젝트에 VibeLign 메타데이터를 초기화")
    p.set_defaults(func=run_vib_init_cli)

    p = sub.add_parser("start", help="처음 쓰는 사람용 시작 명령")
    p.add_argument("message", nargs="*", help="원하면 바로 저장할 체크포인트 메시지")
    p.set_defaults(func=run_vib_start)

    p = sub.add_parser("checkpoint", help="현재 상태를 체크포인트로 저장")
    p.add_argument("message", nargs="*", help="체크포인트 메시지")
    p.set_defaults(func=run_vib_checkpoint)

    p = sub.add_parser("undo", help="최근 체크포인트로 되돌리기")
    p.add_argument("--list", action="store_true", help="체크포인트 목록 보기")
    p.set_defaults(func=run_vib_undo)

    p = sub.add_parser("history", help="체크포인트 이력 보기")
    p.set_defaults(func=run_vib_history)

    p = sub.add_parser("protect", help="중요 파일을 AI 수정으로부터 보호")
    p.add_argument("file", nargs="?", help="보호할 파일명")
    p.add_argument("--remove", action="store_true", help="보호 해제")
    p.add_argument("--list", action="store_true", help="보호 목록 보기")
    p.set_defaults(func=run_protect)

    p = sub.add_parser("ask", help="파일 내용을 쉬운 말로 설명")
    p.add_argument("file", help="설명이 필요한 파일명")
    p.add_argument("question", nargs="*", help="특정 질문")
    p.add_argument("--write", action="store_true", help="프롬프트를 파일로 저장")
    p.set_defaults(func=run_ask)

    p = sub.add_parser("config", help="API 키 설정")
    p.set_defaults(func=run_config)

    p = sub.add_parser("doctor", help="PRD 스타일의 VibeLign 프로젝트 진단")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--detailed", action="store_true")
    p.add_argument("--fix-hints", action="store_true")
    p.add_argument("--write-report", action="store_true")
    p.set_defaults(func=run_vib_doctor)

    p = sub.add_parser("anchor", help="VibeLign 앵커 추천/삽입/검증")
    p.add_argument("--suggest", action="store_true")
    p.add_argument("--auto", action="store_true")
    p.add_argument("--validate", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--only-ext", default="")
    p.set_defaults(func=run_vib_anchor)

    p = sub.add_parser("patch", help="CodeSpeak-ready 패치 계획 생성")
    p.add_argument("request", nargs="+")
    p.add_argument("--ai", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--write-report", action="store_true")
    p.set_defaults(func=run_vib_patch)

    p = sub.add_parser("explain", help="최근 변경을 쉬운 말로 설명 (파일 지정 가능)")
    p.add_argument(
        "file", nargs="?", default=None, help="특정 파일만 설명 (예: main.py)"
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--ai", action="store_true")
    p.add_argument("--since-minutes", type=int, default=120)
    p.add_argument("--write-report", action="store_true")
    p.set_defaults(func=run_vib_explain)

    p = sub.add_parser("guard", help="최근 변경과 구조 위험을 함께 검증")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--since-minutes", type=int, default=120)
    p.add_argument("--write-report", action="store_true")
    p.set_defaults(func=run_vib_guard)

    p = sub.add_parser("export", help="도우미 템플릿 내보내기")
    p.add_argument("tool", choices=["claude", "opencode", "cursor", "antigravity"])
    p.set_defaults(func=run_export)

    p = sub.add_parser("watch", help="실시간 구조 모니터링")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--write-log", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--debounce-ms", type=int, default=800)
    p.set_defaults(func=run_watch_cmd)

    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
# === ANCHOR: VIB_CLI_END ===
