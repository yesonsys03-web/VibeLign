import argparse
from vibeguard.commands.doctor_cmd import run_doctor
from vibeguard.commands.anchor_cmd import run_anchor
from vibeguard.commands.patch_cmd import run_patch
from vibeguard.commands.explain_cmd import run_explain
from vibeguard.commands.guard_cmd import run_guard
from vibeguard.commands.export_cmd import run_export
from vibeguard.commands.watch_cmd import run_watch_cmd
from vibeguard.commands.init_cmd import run_init
from vibeguard.commands.checkpoint_cmd import run_checkpoint
from vibeguard.commands.undo_cmd import run_undo
from vibeguard.commands.protect_cmd import run_protect
from vibeguard.commands.ask_cmd import run_ask
from vibeguard.commands.history_cmd import run_history

def build_parser():
    parser = argparse.ArgumentParser(prog="vibeguard", description="바이브코더를 위한 AI 코딩 안전 시스템")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="프로젝트 초기 설정 (AI 규칙 파일 + 첫 체크포인트)")
    p.add_argument("--tool", default="opencode", choices=["claude", "opencode", "cursor", "antigravity"],
                   help="사용할 AI 도구 (기본값: opencode)")
    p.set_defaults(func=run_init)

    p = sub.add_parser("checkpoint", help="현재 상태를 세이브 포인트로 저장")
    p.add_argument("message", nargs="*", help="체크포인트 메시지 (예: '로그인 기능 완성')")
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
    p.add_argument("--write", action="store_true", help="VIBEGUARD_ASK.md 파일로 저장")
    p.set_defaults(func=run_ask)

    p = sub.add_parser("history", help="체크포인트 저장 이력 보기")
    p.set_defaults(func=run_history)

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

    p = sub.add_parser("explain", help="최근 변경사항을 쉬운 말로 설명")
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
