# === ANCHOR: VIB_CLI_START ===
import argparse
import importlib
import sys

from .commands.vib_anchor_cmd import run_vib_anchor
from .commands.vib_manual_cmd import run_vib_manual
from .commands.vib_checkpoint_cmd import run_vib_checkpoint
from .commands.vib_doctor_cmd import run_vib_doctor
from .commands.vib_explain_cmd import run_vib_explain
from .commands.vib_history_cmd import run_vib_history
from .commands.init_cmd import run_init
from .commands.install_guide_cmd import run_install_guide
from .commands.vib_patch_cmd import run_vib_patch
from .commands.vib_start_cmd import run_vib_start
from .commands.vib_undo_cmd import run_vib_undo
from .commands.vib_scan_cmd import run_vib_scan
from vibelign.commands.ask_cmd import run_ask
from vibelign.commands.config_cmd import run_config
from vibelign.commands.export_cmd import run_export
from vibelign.commands.protect_cmd import run_protect
from vibelign.commands.vib_bench_cmd import run_vib_bench
from vibelign.commands.watch_cmd import run_watch_cmd
from vibelign.terminal_render import print_cli_help


class RichArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
        super().__init__(*args, **kwargs)

    def _print_message(self, message, file=None):
        if not message:
            return
        if file not in (None, sys.stdout):
            file.write(message)
            return
        print_cli_help(str(message))


_MAIN_DESCRIPTION = """\
VibeLign - AI한테 코딩 시켜도 안전하게 지켜주는 도구

처음 시작:
  start       프로젝트 세팅 (AGENTS.md 등 필요 파일 자동 생성)
  init        VibeLign 소스 수정 후 재설치할 때 사용
  install     단계별 설치 방법 안내

세이브 & 되돌리기:
  checkpoint  게임 세이브처럼 지금 상태를 저장해요
  undo        저장한 곳으로 되돌려요
  history     저장 목록을 봐요

점검 & 확인:
  doctor      프로젝트 건강 상태를 확인해요
  guard       AI가 코드를 망가뜨리지 않았는지 검사해요
  explain     뭐가 바뀌었는지 쉽게 알려줘요

AI 수정 요청:
  patch       말로 요청하면 안전한 수정 계획을 만들어요
  anchor      AI가 건드려도 되는 안전 구역을 표시해요
  scan        앵커 스캔 + 코드맵 갱신을 한 번에 해요

파일 & 설정:
  protect     중요한 파일을 잠가요
  ask         파일이 뭘 하는지 설명해줘요
  config      API 키 설정
  export      AI 도구용 설정 내보내기
  watch       실시간 감시

도움말:
  manual      코알못을 위한 상세 사용 설명서"""

_MAIN_EPILOG = """\
처음이세요? 이것만 따라하세요:
  1. vib start              처음 한 번만!
  2. vib checkpoint "저장"  작업 전에 세이브
  3. vib doctor             상태 확인

자세한 사용법: vib <명령어> --help

설치: pip install vibelign  또는  uv tool install vibelign
자세한 설치 방법 (터미널 여는 법 + uv 설치 포함): vib install --help"""


def build_parser():
    run_vib_guard = importlib.import_module(
        "vibelign.commands.vib_guard_cmd"
    ).run_vib_guard
    parser = RichArgumentParser(
        prog="vib",
        description=_MAIN_DESCRIPTION,
        epilog=_MAIN_EPILOG,
    )
    sub = parser.add_subparsers(
        dest="command", required=True, parser_class=RichArgumentParser
    )

    # ── 처음 시작 ──
    p = sub.add_parser(
        "install",
        help="단계별 설치 방법 안내",
        description=(
            "VibeLign을 처음 설치하는 방법을 단계별로 안내해요.\n"
            "터미널 여는 법부터 uv 설치, vibelign 설치까지 모두 설명해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib install        설치 방법 보기\n"
            "  vib install --help 이 안내 보기"
        ),
    )
    p.set_defaults(func=run_install_guide)

    p = sub.add_parser(
        "init",
        help="VibeLign을 다시 설치해요",
        description=(
            "VibeLign을 최신 버전으로 다시 설치해요.\n"
            "코드가 업데이트되면 이 명령어로 새로 깔아주세요.\n"
            "uv 또는 pip을 자동으로 사용해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib init           최신 버전으로 재설치\n"
            "  vib init --force   강제로 다시 설치"
        ),
    )
    p.add_argument("--force", action="store_true", help="강제로 다시 설치")
    p.set_defaults(func=run_init)

    p = sub.add_parser(
        "start",
        help="안심하고 바이브코딩 시작!",
        description=(
            "안심하고 바이브코딩을 시작하세요!\n"
            "AI한테 코딩을 시키기 전에, 이 명령어로 안전하게 준비해요.\n"
            "AGENTS.md, AI_DEV_SYSTEM_SINGLE_FILE.md 등 필요한 파일을 자동으로 만들어줘요.\n"
            "기존 코드를 건드리지 않아요. 걱정 마세요!"
        ),
        epilog=(
            '이렇게 쓰세요:\n'
            '  vib start   새 프로젝트 또는 VibeLign 처음 사용하는 프로젝트 세팅\n'
            '\n'
            'VibeLign 자체를 재설치하려면:\n'
            '  vib init'
        ),
    )
    p.add_argument("--quickstart", action="store_true",
                   help="start + anchor를 한 번에 실행해요")
    p.add_argument("message", nargs="*", help="저장할 메시지 (안 써도 돼요)")
    p.set_defaults(func=run_vib_start)

    # ── 세이브 & 되돌리기 ──
    p = sub.add_parser(
        "checkpoint",
        help="게임 세이브처럼 지금 상태를 저장해요",
        description=(
            "현재 프로젝트 상태를 세이브 포인트로 저장해요.\n"
            "AI가 뭔가 망가뜨려도 이 지점으로 되돌릴 수 있어요."
        ),
        epilog=(
            '이렇게 쓰세요:\n'
            '  vib checkpoint              빠르게 저장\n'
            '  vib checkpoint "로그인 완성"  메시지와 함께 저장'
        ),
    )
    p.add_argument("message", nargs="*", help="저장할 메시지 (안 써도 돼요)")
    p.set_defaults(func=run_vib_checkpoint)

    p = sub.add_parser(
        "undo",
        help="저장한 곳으로 되돌려요",
        description=(
            "마지막 체크포인트로 되돌려요.\n"
            "AI가 코드를 망가뜨렸을 때 쓰세요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib undo         마지막 저장으로 되돌리기\n"
            "  vib undo --list  저장 목록 보기"
        ),
    )
    p.add_argument("--list", action="store_true", help="체크포인트 목록 보기")
    p.set_defaults(func=run_vib_undo)

    p = sub.add_parser(
        "history",
        help="저장 목록을 봐요",
        description="지금까지 저장한 체크포인트 목록을 보여줘요.",
        epilog="이렇게 쓰세요:\n  vib history    저장 기록 보기",
    )
    p.set_defaults(func=run_vib_history)

    # ── 파일 & 설정 ──
    p = sub.add_parser(
        "protect",
        help="중요한 파일을 잠가요",
        description=(
            "AI가 건드리면 안 되는 중요한 파일을 보호해요.\n"
            "보호된 파일은 AI가 수정할 수 없어요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib protect main.py              파일 보호\n"
            "  vib protect --list               보호 목록 보기\n"
            "  vib protect main.py --remove     보호 해제"
        ),
    )
    p.add_argument("file", nargs="?", help="보호할 파일 이름")
    p.add_argument("--remove", action="store_true", help="보호 해제")
    p.add_argument("--list", action="store_true", help="보호 목록 보기")
    p.set_defaults(func=run_protect)

    p = sub.add_parser(
        "ask",
        help="파일이 뭘 하는지 설명해줘요",
        description=(
            "파일이 무슨 일을 하는지 쉬운 말로 설명해줘요.\n"
            "AI가 알아서 분석해서 알려줘요."
        ),
        epilog=(
            '이렇게 쓰세요:\n'
            '  vib ask main.py              파일 설명\n'
            '  vib ask main.py "이거 뭐야?"  질문하기\n'
            '  vib ask main.py --write      설명을 파일로 저장'
        ),
    )
    p.add_argument("file", help="설명할 파일 이름")
    p.add_argument("question", nargs="*", help="궁금한 것 (안 써도 돼요)")
    p.add_argument("--write", action="store_true", help="설명을 파일로 저장")
    p.set_defaults(func=run_ask)

    p = sub.add_parser(
        "config",
        help="API 키 설정",
        description=(
            "AI 기능을 쓰려면 API 키가 필요해요.\n"
            "이 명령어로 설정할 수 있어요."
        ),
        epilog="이렇게 쓰세요:\n  vib config    API 키 설정하기",
    )
    p.set_defaults(func=run_config)

    # ── 점검 & 확인 ──
    p = sub.add_parser(
        "doctor",
        help="프로젝트 건강 상태를 확인해요",
        description=(
            "프로젝트가 AI 수정을 받아도 괜찮은지 점검해요.\n"
            "문제가 있으면 어디가 아픈지 알려줘요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib doctor             기본 점검\n"
            "  vib doctor --strict    꼼꼼하게 점검\n"
            "  vib doctor --detailed  자세한 설명 포함\n"
            "  vib doctor --fix       앵커 없는 파일에 자동으로 앵커 추가"
        ),
    )
    p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.add_argument("--strict", action="store_true", help="더 꼼꼼하게 점검")
    p.add_argument("--detailed", action="store_true", help="문제마다 자세한 설명")
    p.add_argument("--fix-hints", action="store_true", help="고치는 방법 힌트")
    p.add_argument("--fix", action="store_true", help="앵커 없는 파일에 자동으로 앵커 추가")
    p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    p.set_defaults(func=run_vib_doctor)

    p = sub.add_parser(
        "anchor",
        help="AI가 건드려도 되는 안전 구역을 표시해요",
        description=(
            "코드에 안전 구역(앵커)을 표시해요.\n"
            "AI가 이 구역 안에서만 수정하도록 안내해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib anchor --suggest   앵커 추천 받기\n"
            "  vib anchor --auto      자동으로 앵커 삽입\n"
            "  vib anchor --validate  앵커 검증"
        ),
    )
    p.add_argument("--suggest", action="store_true", help="앵커 추천 받기")
    p.add_argument("--auto", action="store_true", help="자동으로 앵커 삽입")
    p.add_argument("--validate", action="store_true", help="앵커 검증")
    p.add_argument("--dry-run", action="store_true", help="실제로 바꾸지 않고 미리 보기")
    p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.add_argument("--only-ext", default="", help="특정 확장자만 (.py, .js 등)")
    p.set_defaults(func=run_vib_anchor)

    p = sub.add_parser(
        "patch",
        help="말로 요청하면 안전한 수정 계획을 만들어요",
        description=(
            '"로그인 버튼 추가해줘" 같이 말로 요청하면\n'
            "어떤 파일의 어느 부분을 수정할지 계획을 세워요."
        ),
        epilog=(
            '이렇게 쓰세요:\n'
            '  vib patch "로그인 버튼 추가"           수정 계획\n'
            '  vib patch "버그 수정" --ai             AI가 분석\n'
            '  vib patch "사이드바 제거" --preview    미리 보기'
        ),
    )
    p.add_argument("request", nargs="+", help="수정 요청 (말로 써주세요)")
    p.add_argument("--ai", action="store_true", help="AI가 더 정확하게 분석")
    p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.add_argument("--preview", action="store_true", help="수정 미리 보기")
    p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    p.add_argument("--copy", action="store_true", help="AI 전달용 프롬프트를 클립보드에 복사")
    p.set_defaults(func=run_vib_patch)

    p = sub.add_parser(
        "explain",
        help="뭐가 바뀌었는지 쉽게 알려줘요",
        description=(
            "최근에 뭐가 바뀌었는지 쉬운 말로 설명해줘요.\n"
            "AI가 코드를 바꿨을 때 확인하세요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib explain              전체 변경 설명\n"
            "  vib explain main.py      특정 파일만 설명\n"
            "  vib explain --ai         AI가 더 자세하게"
        ),
    )
    p.add_argument(
        "file", nargs="?", default=None, help="특정 파일만 설명 (안 써도 돼요)"
    )
    p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.add_argument("--ai", action="store_true", help="AI가 더 자세하게 분석")
    p.add_argument("--since-minutes", type=int, default=120, help="최근 몇 분 동안의 변경 (기본: 120분)")
    p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    p.set_defaults(func=run_vib_explain)

    p = sub.add_parser(
        "guard",
        help="AI가 코드를 망가뜨리지 않았는지 검사해요",
        description=(
            "AI가 코드를 수정한 후, 구조가 망가지지 않았는지 검사해요.\n"
            "doctor + explain을 합친 종합 검진이에요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib guard              기본 검사\n"
            "  vib guard --strict     꼼꼼하게 검사"
        ),
    )
    p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.add_argument("--strict", action="store_true", help="더 꼼꼼하게 검사")
    p.add_argument("--since-minutes", type=int, default=120, help="최근 몇 분 동안의 변경 (기본: 120분)")
    p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    p.set_defaults(func=run_vib_guard)

    p = sub.add_parser(
        "export",
        help="AI 도구용 설정 내보내기",
        description=(
            "Claude, Cursor 같은 AI 도구에서 VibeLign을 쓸 수 있도록\n"
            "설정 파일을 내보내요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib export claude      Claude용 설정\n"
            "  vib export cursor      Cursor용 설정"
        ),
    )
    p.add_argument("tool", choices=["claude", "opencode", "cursor", "antigravity"], help="AI 도구 이름")
    p.set_defaults(func=run_export)

    p = sub.add_parser(
        "scan",
        help="앵커 스캔 + 코드맵 갱신을 한 번에 해요",
        description=(
            "앵커 스캔, 앵커 인덱스 갱신, 코드맵 재생성을 한 번에 실행해요.\n"
            "vib anchor 와 vib start 를 따로 실행하지 않아도 돼요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib scan          앵커 추천 + 코드맵 갱신\n"
            "  vib scan --auto   앵커 자동 삽입 + 코드맵 갱신"
        ),
    )
    p.add_argument("--auto", action="store_true", help="앵커 자동 삽입 (추천만 볼 때는 생략)")
    p.set_defaults(func=run_vib_scan)

    p = sub.add_parser(
        "watch",
        help="실시간 감시",
        description=(
            "파일이 바뀔 때마다 자동으로 구조를 점검해요.\n"
            "AI가 코딩하는 동안 켜두면 좋아요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib watch              실시간 감시 시작\n"
            "  vib watch --strict     꼼꼼 모드"
        ),
    )
    p.add_argument("--strict", action="store_true", help="더 꼼꼼하게 감시")
    p.add_argument("--write-log", action="store_true", help="로그를 파일로 저장")
    p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.add_argument("--debounce-ms", type=int, default=800, help="감시 간격 (밀리초, 기본: 800)")
    p.set_defaults(func=run_watch_cmd)

    # ── 벤치마크 ──
    p = sub.add_parser(
        "bench",
        help="앵커 효과 검증 벤치마크",
        description=(
            "앵커가 AI 코드 수정 정확도를 높이는지 검증하는 벤치마크 도구예요.\n"
            "A(앵커 없음) vs B(앵커 있음) 조건으로 프롬프트를 생성하고,\n"
            "AI 수정 결과를 채점할 수 있어요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib bench --generate    A/B 프롬프트 생성\n"
            "  vib bench --score       AI 수정 결과 채점\n"
            "  vib bench --report      마크다운 리포트 생성"
        ),
    )
    p.add_argument("--generate", action="store_true", help="A/B 조건별 프롬프트 생성")
    p.add_argument("--score", action="store_true", help="AI 수정 결과 채점")
    p.add_argument("--report", action="store_true", help="마크다운 비교 리포트 생성")
    p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.set_defaults(func=run_vib_bench)

    # ── 매뉴얼 ──
    p = sub.add_parser(
        "manual",
        help="코알못을 위한 상세 사용 설명서",
        description=(
            "모든 명령어를 쉬운 말로 설명해줘요.\n"
            "옵션, 예시, 언제 쓰는지까지 전부 알려줘요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib manual                전체 명령어 목록\n"
            "  vib manual checkpoint     checkpoint 상세 보기\n"
            "  vib manual --all          전체 상세 보기\n"
            "  vib manual --save         VIBELIGN_MANUAL.md 파일로 저장"
        ),
    )
    p.add_argument(
        "command_name",
        nargs="?",
        default=None,
        help="상세히 볼 커맨드 이름 (예: checkpoint, anchor, guard ...)",
    )
    p.add_argument("--all", action="store_true", help="전체 커맨드 상세 보기")
    p.add_argument("--save", action="store_true", help="VIBELIGN_MANUAL.md 파일로 저장")
    p.set_defaults(func=run_vib_manual)

    # ── 쉘 자동완성 ──
    p = sub.add_parser(
        "completion",
        help="탭 자동완성 설정 (zsh/bash/PowerShell)",
        description=(
            "vib 명령어의 탭 자동완성을 설정해요.\n"
            "한 번만 설정하면 vib + 탭키로 명령어가 자동 완성돼요.\n"
            "macOS/Linux: zsh, bash 지원\n"
            "Windows: PowerShell 지원"
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib completion            설정 방법 안내\n"
            "  vib completion --install  자동으로 설정 (zsh/bash/PowerShell 자동 감지)"
        ),
    )
    p.add_argument("--install", action="store_true", help="자동으로 쉘 프로파일에 설정")
    p.set_defaults(func=lambda args: _run_completion(args, parser))

    return parser


def _parse_commands(parser):
    """parser에서 서브커맨드 목록과 옵션 맵 추출."""
    subparsers_action = None
    for action in parser._subparsers._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break

    commands = []
    cmd_opts = {}
    if subparsers_action:
        for cmd_name, cmd_parser in subparsers_action.choices.items():
            commands.append(cmd_name)
            opts = []
            for act in cmd_parser._actions:
                for opt in act.option_strings:
                    if opt.startswith("--"):
                        opts.append(opt)
            cmd_opts[cmd_name] = opts
    return commands, cmd_opts


def _manual_topics() -> str:
    """vib manual 의 positional 완성 목록."""
    try:
        from vibelign.commands.vib_manual_cmd import MANUAL
        return " ".join(MANUAL.keys())
    except Exception:
        return ""


# positional 완성이 필요한 커맨드: {커맨드명: [완성 목록]}
_POSITIONAL_COMPLETIONS: dict[str, list[str]] = {
    "export": ["claude", "opencode", "cursor", "antigravity"],
}


def _generate_completion_script(parser) -> str:
    """zsh/bash 자동완성 스크립트 생성 (eval "$(vib completion)" 용)."""
    commands, cmd_opts = _parse_commands(parser)
    cmds_str = " ".join(commands)
    manual_topics = _manual_topics()

    case_lines = []
    for cmd in commands:
        opts_str = " ".join(cmd_opts[cmd])
        if cmd == "manual":
            all_completions = f"{manual_topics} {opts_str}".strip()
            case_lines.append(f'        manual) opts="{all_completions}" ;;')
        elif cmd in _POSITIONAL_COMPLETIONS:
            positional_str = " ".join(_POSITIONAL_COMPLETIONS[cmd])
            all_completions = f"{positional_str} {opts_str}".strip()
            case_lines.append(f'        {cmd}) opts="{all_completions}" ;;')
        else:
            case_lines.append(f'        {cmd}) opts="{opts_str}" ;;')
    case_block = "\n".join(case_lines)

    return f'''# VibeLign (vib) 쉘 자동완성
# 이 스크립트는 vib completion 으로 자동 생성되었습니다.

if [ -n "${{ZSH_VERSION:-}}" ]; then
    # ── zsh ──
    autoload -Uz compinit 2>/dev/null
    if ! type compdef &>/dev/null; then
        compinit -i 2>/dev/null
    fi
    _vib_zsh() {{
        local -a commands
        commands=({cmds_str})

        if (( CURRENT == 2 )); then
            compadd -a commands
            return
        fi

        local opts
        case "${{words[2]}}" in
{case_block}
            *) opts="" ;;
        esac

        compadd -- ${{(s: :)opts}}
    }}
    compdef _vib_zsh vib
else
    # ── bash ──
    _vib_completions() {{
        local cur prev commands opts
        COMPREPLY=()
        cur="${{COMP_WORDS[COMP_CWORD]}}"
        prev="${{COMP_WORDS[COMP_CWORD-1]}}"
        commands="{cmds_str}"

        if [[ ${{COMP_CWORD}} -eq 1 ]]; then
            COMPREPLY=( $(compgen -W "${{commands}}" -- "${{cur}}") )
            return 0
        fi

        case "${{COMP_WORDS[1]}}" in
{case_block}
            *) opts="" ;;
        esac

        COMPREPLY=( $(compgen -W "${{opts}}" -- "${{cur}}") )
        return 0
    }}
    complete -F _vib_completions vib
fi
'''


def _generate_powershell_script(parser) -> str:
    """PowerShell 자동완성 스크립트 생성."""
    commands, cmd_opts = _parse_commands(parser)
    manual_topics = _manual_topics().split()

    cmds_ps = ", ".join(f"'{c}'" for c in commands)

    opts_lines = []
    for cmd in commands:
        base_opts = cmd_opts.get(cmd, [])
        if cmd == "manual":
            all_items = manual_topics + base_opts
        elif cmd in _POSITIONAL_COMPLETIONS:
            all_items = _POSITIONAL_COMPLETIONS[cmd] + base_opts
        else:
            all_items = base_opts
        if all_items:
            opts_ps = ", ".join(f"'{o}'" for o in all_items)
            opts_lines.append(f"    '{cmd}' = @({opts_ps})")
        else:
            opts_lines.append(f"    '{cmd}' = @()")
    opts_block = "\n".join(opts_lines)

    return f"""# VibeLign (vib) PowerShell 탭 자동완성
# 이 스크립트는 vib completion --install 로 자동 추가되었습니다.

Register-ArgumentCompleter -Native -CommandName vib -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @({cmds_ps})
    $cmdOpts = @{{
{opts_block}
    }}

    $words = $commandAst.CommandElements
    if ($words.Count -le 2) {{
        $commands | Where-Object {{ $_ -like "$wordToComplete*" }} |
            ForEach-Object {{
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }}
    }} else {{
        $cmd = $words[1].Value
        if ($cmdOpts.ContainsKey($cmd)) {{
            $cmdOpts[$cmd] | Where-Object {{ $_ -like "$wordToComplete*" }} |
                ForEach-Object {{
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
                }}
        }}
    }}
}}
"""


def _run_completion(args, parser):
    """쉘 자동완성 설정."""
    import os
    import sys
    from vibelign.terminal_render import clack_info, clack_intro, clack_outro, clack_success, clack_warn

    is_windows = sys.platform == "win32"

    if getattr(args, "install", False):
        if is_windows:
            _install_completion_powershell(parser, clack_info, clack_success, clack_warn)
        else:
            _install_completion_posix(parser, clack_info, clack_success, clack_warn)
        return

    clack_intro("VibeLign 탭 자동완성 설정")
    clack_info("방법 1 (자동 설정, 추천):")
    clack_info("  vib completion --install")
    clack_info("")
    if is_windows:
        clack_info("방법 2 (수동 설정 - PowerShell):")
        clack_info("  $PROFILE 파일에 아래를 추가하세요:")
        clack_info("  Invoke-Expression (vib completion)")
    else:
        clack_info("방법 2 (수동 설정 - zsh/bash):")
        clack_info("  아래 명령어를 ~/.zshrc 또는 ~/.bashrc 에 추가하세요:")
        clack_info('  eval "$(vib completion)"')
    clack_outro("설정 후 새 터미널을 열면 vib + 탭키가 작동해요!")


def _install_completion_posix(parser, clack_info, clack_success, clack_warn):
    """macOS/Linux: zsh/bash 프로파일에 자동완성 스크립트 추가."""
    import os

    script = _generate_completion_script(parser)
    shell = os.environ.get("SHELL", "")

    if "zsh" in shell:
        profile = os.path.expanduser("~/.zshrc")
    elif "bash" in shell:
        profile = os.path.expanduser("~/.bashrc")
        if not os.path.exists(profile):
            profile = os.path.expanduser("~/.bash_profile")
    else:
        clack_warn("지원하지 않는 쉘이에요. 아래 스크립트를 직접 추가해주세요.")
        print(script)
        return

    comp_dir = os.path.expanduser("~/.vibelign")
    os.makedirs(comp_dir, exist_ok=True)
    comp_file = os.path.join(comp_dir, "completion.sh")

    with open(comp_file, "w", encoding="utf-8") as f:
        f.write(script)

    source_line = f'[ -f "{comp_file}" ] && source "{comp_file}"'

    profile_text = ""
    if os.path.exists(profile):
        profile_text = open(profile, encoding="utf-8", errors="ignore").read()

    if comp_file in profile_text:
        clack_success("자동완성 스크립트를 갱신했어요! 새 터미널을 열면 적용돼요.")
    else:
        with open(profile, "a", encoding="utf-8") as f:
            f.write(f"\n# VibeLign 탭 자동완성\n{source_line}\n")
        clack_success(f"자동완성 설정 완료! ({profile}에 추가)")
        clack_info("새 터미널을 열면 vib + 탭키로 명령어가 자동 완성돼요.")
        clack_info(f"지금 바로 쓰려면: source {profile}")


def _install_completion_powershell(parser, clack_info, clack_success, clack_warn):
    """Windows: PowerShell 프로파일에 자동완성 스크립트 추가."""
    import os
    from pathlib import Path

    script = _generate_powershell_script(parser)

    comp_dir = Path.home() / ".vibelign"
    comp_dir.mkdir(exist_ok=True)
    comp_file = comp_dir / "completion.ps1"
    comp_file.write_text(script, encoding="utf-8")

    # PowerShell 프로파일 경로 (PS 7+ 우선, 없으면 PS 5)
    ps7_profile = Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
    ps5_profile = Path.home() / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
    profile = ps7_profile if ps7_profile.parent.exists() else ps5_profile

    profile.parent.mkdir(parents=True, exist_ok=True)

    source_line = f'. "{comp_file}"'
    profile_text = profile.read_text(encoding="utf-8", errors="ignore") if profile.exists() else ""

    if str(comp_file) in profile_text:
        clack_success("자동완성 스크립트를 갱신했어요! 새 PowerShell 창을 열면 적용돼요.")
    else:
        with open(profile, "a", encoding="utf-8") as f:
            f.write(f"\n# VibeLign 탭 자동완성\n{source_line}\n")
        clack_success(f"자동완성 설정 완료! ({profile}에 추가)")
        clack_info("새 PowerShell 창을 열면 vib + 탭키로 명령어가 자동 완성돼요.")
        clack_info(f"지금 바로 쓰려면: . {profile}")


def main():
    parser = build_parser()
    # eval "$(vib completion)" 지원: stdout이 파이프면 스크립트 직접 출력
    if len(sys.argv) == 2 and sys.argv[1] == "completion" and not sys.stdout.isatty():
        print(_generate_completion_script(parser))
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
# === ANCHOR: VIB_CLI_END ===
