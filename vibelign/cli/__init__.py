# === ANCHOR: CLI_START ===
import argparse
import sys
from vibelign.commands.doctor_cmd import run_doctor
from vibelign.commands.anchor_cmd import run_anchor
from vibelign.commands.patch_cmd import run_patch
from vibelign.commands.explain_cmd import run_explain
from vibelign.commands.guard_cmd import run_guard
from vibelign.commands.export_cmd import run_export
from vibelign.commands.watch_cmd import run_watch_cmd
from vibelign.commands.init_cmd import run_init
from vibelign.commands.checkpoint_cmd import run_checkpoint
from vibelign.commands.undo_cmd import run_undo
from vibelign.commands.protect_cmd import run_protect
from vibelign.commands.vib_secrets_cmd import run_vib_secrets
from vibelign.commands.ask_cmd import run_ask
from vibelign.commands.history_cmd import run_history
from vibelign.commands.config_cmd import run_config
from vibelign.commands.vib_start_cmd import run_vib_start
from vibelign.terminal_render import print_cli_help


# === ANCHOR: CLI_RICHARGUMENTPARSER_START ===
class RichArgumentParser(argparse.ArgumentParser):
    # === ANCHOR: CLI__PRINT_MESSAGE_START ===
    def _print_message(self, message, file=None):
        if not message:
            return
        if file not in (None, sys.stdout):
            file.write(message)
            return
        # === ANCHOR: CLI_RICHARGUMENTPARSER_END ===
        print_cli_help(str(message))

    # === ANCHOR: CLI__PRINT_MESSAGE_END ===


_EPILOG = """
─────────────────────────────────────────────────
 설치 방법
─────────────────────────────────────────────────
 [uv 사용 (권장)]
   uv tool install vibelign

 [pip 사용]
   pip install vibelign
─────────────────────────────────────────────────
  vibelign 명령어가 실행되지 않을 때 (PATH 설정)
─────────────────────────────────────────────────
 [Mac / Linux]
   1. 터미널에서 아래 명령어 실행:
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
      source ~/.zshrc

   2. 그래도 안 되면:
      uv tool update-shell
      (새 터미널 창 열기)

 [Windows]
   1. 명령 프롬프트(CMD) 또는 PowerShell에서:
      uv tool update-shell
      (새 터미널 창 열기)

   2. 그래도 안 되면 직접 PATH 추가:
      시스템 환경 변수 → Path → 새로 만들기:
      %USERPROFILE%\\.local\\bin
─────────────────────────────────────────────────
 업데이트 후 변경사항이 반영되지 않을 때 (재설치)
─────────────────────────────────────────────────
 [uv 사용]
   Mac / Linux:
      uv tool uninstall vibelign && uv tool install . --no-cache
   Windows:
      uv tool uninstall vibelign
     uv tool install . --no-cache

 [pip 사용]
   Mac / Linux:
      pip uninstall vibelign -y && pip install . --no-cache-dir
   Windows:
      pip uninstall vibelign -y
     pip install . --no-cache-dir
─────────────────────────────────────────────────
"""


# === ANCHOR: CLI_BUILD_PARSER_START ===
def build_parser():
    parser = RichArgumentParser(
        prog="vibelign",
        description="바이브코더를 위한 AI 코딩 안전 시스템",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(
        dest="command", required=True, parser_class=RichArgumentParser
    )

    p = sub.add_parser("start", help="프로젝트 시작 설정 (AI 도구 연동 + 상태 확인)")
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--all-tools", action="store_true", help="모든 지원 도구를 한 번에 준비"
    )
    group.add_argument("--tools", default=None)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=run_vib_start)

    p = sub.add_parser("init", help="VibeLign 업데이트 / 재설치 (pip·uv 자동 감지)")
    p.add_argument(
        "--force", action="store_true", help="이미 최신 버전이어도 강제로 재설치"
    )
    p.set_defaults(func=run_init)

    p = sub.add_parser("checkpoint", help="현재 상태를 세이브 포인트로 저장")
    p.add_argument(
        "message", nargs="*", help="체크포인트 메시지 (예: '로그인 기능 완성')"
    )
    p.set_defaults(func=run_checkpoint)

    p = sub.add_parser("undo", help="마지막 체크포인트로 되돌리기")
    p.add_argument("--list", action="store_true", help="저장된 체크포인트 목록 보기")
    p.set_defaults(func=run_undo)

    p = sub.add_parser("protect", help="중요 파일을 AI 수정으로부터 보호")
    p.add_argument("file", nargs="?", help="보호할 파일명 (예: main.py)")
    p.add_argument("--remove", action="store_true", help="보호 해제")
    p.add_argument("--list", action="store_true", help="보호 목록 보기")
    p.set_defaults(func=run_protect)

    p = sub.add_parser("ask", help="파일 내용을 쉬운 말로 설명하는 AI 프롬프트 생성")
    p.add_argument("file", help="설명이 필요한 파일명 (예: login.py)")
    p.add_argument("question", nargs="*", help="특정 질문 (선택사항)")
    p.add_argument("--write", action="store_true", help="VIBELIGN_ASK.md 파일로 저장")
    p.set_defaults(func=run_ask)

    p = sub.add_parser("history", help="체크포인트 저장 이력 보기")
    p.set_defaults(func=run_history)

    p = sub.add_parser("config", help="API 키 설정 (Anthropic / Gemini)")
    p.set_defaults(func=run_config)

    p = sub.add_parser("secrets", help="지금 커밋할 내용 검사 + 자동 검사 연결 관리")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--install-hook", action="store_true")
    p.add_argument("--uninstall-hook", action="store_true")
    p.set_defaults(func=run_vib_secrets)

    p = sub.add_parser("doctor", help="프로젝트 구조 진단")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=run_doctor)

    p = sub.add_parser("anchor", help="소스 파일에 모듈 앵커 삽입")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only-ext", default="")
    p.set_defaults(func=run_anchor)

    p = sub.add_parser("patch", help="스마트 패치 프롬프트 준비")
    p.add_argument("request", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=run_patch)

    p = sub.add_parser(
        "explain", help="최근 변경사항을 쉬운 말로 설명 (파일 지정 가능)"
    )
    p.add_argument(
        "file", nargs="?", default=None, help="특정 파일만 설명 (예: main.py)"
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--since-minutes", type=int, default=120)
    p.add_argument("--write-report", action="store_true")
    p.set_defaults(func=run_explain)

    p = sub.add_parser("guard", help="doctor와 explain을 합친 안전 리포트 생성")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--since-minutes", type=int, default=120)
    p.add_argument("--write-report", action="store_true")
    p.set_defaults(func=run_guard)

    p = sub.add_parser("export", help="도우미 템플릿 내보내기")
    p.add_argument(
        "tool", choices=["claude", "opencode", "cursor", "antigravity", "codex"]
    )
    p.set_defaults(func=run_export)

    p = sub.add_parser("watch", help="실시간 구조 모니터링")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--auto-fix", action="store_true")
    p.add_argument("--write-log", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--debounce-ms", type=int, default=800)
    p.set_defaults(func=run_watch_cmd)
    return parser


# === ANCHOR: CLI_BUILD_PARSER_END ===


# === ANCHOR: CLI_MAIN_START ===
def main():
    args = build_parser().parse_args()
    args.func(args)


# === ANCHOR: CLI_MAIN_END ===


if __name__ == "__main__":
    main()
# === ANCHOR: CLI_END ===
