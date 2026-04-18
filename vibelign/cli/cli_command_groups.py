# === ANCHOR: CLI_COMMAND_GROUPS_START ===
import argparse
import importlib
from collections.abc import Callable
from typing import Protocol, cast


# === ANCHOR: CLI_COMMAND_GROUPS_SUBPARSERFACTORY_START ===
class SubparserFactory(Protocol):
    # === ANCHOR: CLI_COMMAND_GROUPS_ADD_PARSER_START ===
    def add_parser(
        self,
        name: str,
        *,
        help: str | None = None,
        description: str | None = None,
        epilog: str | None = None,
        **kwargs: object,
        # === ANCHOR: CLI_COMMAND_GROUPS_SUBPARSERFACTORY_END ===
        # === ANCHOR: CLI_COMMAND_GROUPS_ADD_PARSER_END ===
    ) -> argparse.ArgumentParser: ...


# === ANCHOR: CLI_COMMAND_GROUPS__RUN_VIB_MANUAL_START ===
def _run_vib_manual(args: object) -> None:
    run_vib_manual = cast(
        Callable[[object], None],
        importlib.import_module("vibelign.commands.vib_manual_cmd").run_vib_manual,
    )
    run_vib_manual(args)


# === ANCHOR: CLI_COMMAND_GROUPS__RUN_VIB_MANUAL_END ===


# === ANCHOR: CLI_COMMAND_GROUPS__RUN_VIB_RULES_START ===
def _run_vib_rules(_: object) -> None:
    run_vib_manual = cast(
        Callable[[object], None],
        importlib.import_module("vibelign.commands.vib_manual_cmd").run_vib_manual,
    )
    run_vib_manual(
        argparse.Namespace(command_name="rules", save=False, all=False, json=False)
    )


# === ANCHOR: CLI_COMMAND_GROUPS__RUN_VIB_RULES_END ===


# === ANCHOR: CLI_COMMAND_GROUPS_REGISTER_EXTENDED_COMMANDS_START ===
def register_extended_commands(
    sub: SubparserFactory,
    lazy_command: Callable[[str, str], Callable[[object], None]],
    run_vib_guard: Callable[[object], None],
    # === ANCHOR: CLI_COMMAND_GROUPS_REGISTER_EXTENDED_COMMANDS_END ===
) -> None:
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
    _ = p.add_argument("file", nargs="?", help="보호할 파일 이름")
    _ = p.add_argument("--remove", action="store_true", help="보호 해제")
    _ = p.add_argument("--list", action="store_true", help="보호 목록 보기")
    p.set_defaults(func=lazy_command("vibelign.commands.protect_cmd", "run_protect"))

    p = sub.add_parser(
        "ask",
        help="파일이 뭘 하는지 설명해줘요",
        description=(
            "파일이 무슨 일을 하는지 쉬운 말로 설명해줘요.\n"
            "AI가 알아서 분석해서 알려줘요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib ask main.py              파일 설명\n"
            '  vib ask main.py "이거 뭐야?"  질문하기\n'
            "  vib ask main.py --write      설명을 파일로 저장"
        ),
    )
    _ = p.add_argument("file", help="설명할 파일 이름")
    _ = p.add_argument("question", nargs="*", help="궁금한 것 (안 써도 돼요)")
    _ = p.add_argument("--write", action="store_true", help="설명을 파일로 저장")
    p.set_defaults(func=lazy_command("vibelign.commands.ask_cmd", "run_ask"))

    p = sub.add_parser(
        "config",
        help="API 키 및 AI 보강 옵트인 설정",
        description=(
            "AI 기능을 쓰려면 API 키가 필요해요.\n"
            "API 키 설정(인터랙티브) + 앵커 AI 보강 on/off 토글을 함께 관리해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib config                               API 키 설정 (인터랙티브)\n"
            "  vib config --ai-enhance status           AI 앵커 보강 상태 조회\n"
            "  vib config --ai-enhance enable           AI 앵커 보강 켜기\n"
            "  vib config --ai-enhance disable          AI 앵커 보강 끄기"
        ),
    )
    _ = p.add_argument(
        "--ai-enhance",
        dest="ai_enhance",
        choices=["enable", "disable", "status"],
        default=None,
        help="앵커 AI intent 자동 보강 on/off 토글 (.vibelign/config.yaml)",
    )
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.set_defaults(func=lazy_command("vibelign.commands.config_cmd", "run_config"))

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
            "  vib doctor --fix       앵커 없는 파일에 자동으로 앵커 추가\n"
            "  vib doctor --plan      실행 계획 출력 (파일 수정 없음)"
        ),
    )
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    _ = p.add_argument("--strict", action="store_true", help="더 꼼꼼하게 점검")
    _ = p.add_argument("--detailed", action="store_true", help="문제마다 자세한 설명")
    _ = p.add_argument("--fix-hints", action="store_true", help="고치는 방법 힌트")
    _ = p.add_argument(
        "--fix", action="store_true", help="앵커 없는 파일에 자동으로 앵커 추가"
    )
    _ = p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    plan_group = p.add_mutually_exclusive_group()
    _ = plan_group.add_argument(
        "--plan", action="store_true", help="실행 계획 출력 (파일 수정 없음)"
    )
    _ = plan_group.add_argument(
        "--patch", action="store_true", help="변경 예정 diff 출력 (파일 수정 없음)"
    )
    _ = plan_group.add_argument(
        "--apply", action="store_true", help="자동 리팩토링 실행"
    )
    _ = p.add_argument(
        "--force", action="store_true", help="--apply 확인 프롬프트 생략"
    )
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_doctor_cmd", "run_vib_doctor")
    )

    p = sub.add_parser(
        "anchor",
        help="AI가 건드려도 되는 안전 구역을 표시해요",
        description=(
            "코드에 안전 구역(앵커)을 표시해요.\n"
            "AI가 이 구역 안에서만 수정하도록 안내해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib anchor --suggest                                앵커 추천 받기\n"
            "  vib anchor --auto                                   자동으로 앵커 삽입\n"
            "  vib anchor --auto-intent                            AI가 모든 앵커 intent 자동 생성\n"
            "  vib anchor --validate                               앵커 검증\n"
            '  vib anchor --set-intent ANCHOR_NAME --intent "설명"  앵커 의도 직접 등록\n'
            "  vib anchor --list-intent                            등록된 의도 목록 보기"
        ),
    )
    _ = p.add_argument("--suggest", action="store_true", help="앵커 추천 받기")
    _ = p.add_argument("--auto", action="store_true", help="자동으로 앵커 삽입")
    _ = p.add_argument("--validate", action="store_true", help="앵커 검증")
    _ = p.add_argument(
        "--dry-run", action="store_true", help="실제로 바꾸지 않고 미리 보기"
    )
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    _ = p.add_argument("--only-ext", default="", help="특정 확장자만 (.py, .js 등)")
    _ = p.add_argument(
        "--set-intent",
        metavar="ANCHOR_NAME",
        default=None,
        help="앵커에 의도(intent) 등록",
    )
    _ = p.add_argument(
        "--intent",
        metavar="TEXT",
        default=None,
        help="등록할 의도 텍스트 (--set-intent와 함께 사용)",
    )
    _ = p.add_argument(
        "--list-intent", action="store_true", help="등록된 intent 목록 보기"
    )
    _ = p.add_argument(
        "--auto-intent", action="store_true", help="AI가 모든 앵커 intent 자동 생성"
    )
    _ = p.add_argument(
        "--force",
        action="store_true",
        help="--auto-intent 시 기존 AI 생성 항목도 재생성",
    )
    _ = p.add_argument(
        "--with-ai",
        action="store_true",
        help="--auto-intent 시 AI 보강까지 실행 (기본: 코드 기반만)",
    )
    _ = p.add_argument(
        "--aliases",
        metavar="A,B,C",
        default=None,
        help="--set-intent 보조: 검색 별칭 (쉼표 구분)",
    )
    _ = p.add_argument(
        "--description",
        metavar="TEXT",
        default=None,
        help="--set-intent 보조: 상세 설명",
    )
    _ = p.add_argument(
        "--warning",
        metavar="TEXT",
        default=None,
        help="--set-intent 보조: AI에게 전달할 주의사항",
    )
    _ = p.add_argument(
        "--connects",
        metavar="A,B,C",
        default=None,
        help="--set-intent 보조: 연결 앵커 이름 (쉼표 구분)",
    )
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_anchor_cmd", "run_vib_anchor")
    )

    p = sub.add_parser(
        "patch",
        help="말로 요청하면 안전한 수정 계획을 만들어요",
        description=(
            '"로그인 버튼 추가해줘" 같이 말로 요청하면\n'
            "어떤 파일의 어느 부분을 수정할지 계획을 세워요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            '  vib patch "로그인 버튼 추가"           수정 계획\n'
            '  vib patch "버그 수정" --ai             AI가 분석\n'
            '  vib patch "사이드바 제거" --preview    미리 보기\n'
            "  vib patch --apply-strict patch.json   strict_patch JSON 적용\n"
            "  vib patch --apply-strict patch.json --dry-run   검증만 (파일·체크포인트 없음)\n"
            '  vib patch --lazy-fanout --json "A 그리고 B"   다중 의도 시 첫 조각만 상세 계획'
        ),
    )
    _ = p.add_argument(
        "--apply-strict",
        metavar="FILE",
        default=None,
        help="strict_patch JSON 파일을 검증 후 워크스페이스에 적용",
    )
    _ = p.add_argument(
        "--dry-run",
        action="store_true",
        help="--apply-strict와 함께: 검증만 하고 디스크에 쓰지 않음",
    )
    _ = p.add_argument(
        "request", nargs="*", help="수정 요청 (--apply-strict 없을 때 필요)"
    )
    _ = p.add_argument("--ai", action="store_true", help="AI가 더 정확하게 분석")
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    _ = p.add_argument("--preview", action="store_true", help="수정 미리 보기")
    _ = p.add_argument(
        "--lazy-fanout",
        action="store_true",
        help="다중 의도 시 첫 의도만 계획하고 나머지는 pending_sub_intents로 표시",
    )
    _ = p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    _ = p.add_argument(
        "--copy", action="store_true", help="AI 전달용 프롬프트를 클립보드에 복사"
    )
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_patch_cmd", "run_vib_patch")
    )

    p = sub.add_parser(
        "secrets",
        help="API 키 같은 비밀정보 커밋을 막아요",
        description=(
            "커밋 직전에 지금 올리려는 내용만 검사해서 API 키 같은 비밀정보를 막아요.\n"
            "`vib start`를 했다면 보통 커밋할 때마다 이 검사가 자동으로 돌아가요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib secrets --staged         지금 커밋할 내용 수동 검사 (상시검사)\n"
            "  vib secrets --all            전체 히스토리 정밀검사 (시간 걸림)\n"
            "  vib secrets --install-hook   커밋할 때마다 자동 검사되게 연결\n"
            "  vib secrets --uninstall-hook 자동 검사 연결 해제"
        ),
    )
    _ = p.add_argument("--staged", action="store_true", help="지금 커밋할 내용만 검사")
    _ = p.add_argument(
        "--all",
        action="store_true",
        help="전체 히스토리 정밀검사 (도입 직후·공개 전 권장, 시간 걸림)",
    )
    _ = p.add_argument(
        "--install-hook", action="store_true", help="커밋할 때마다 자동 검사되게 연결"
    )
    _ = p.add_argument(
        "--uninstall-hook", action="store_true", help="자동 검사 연결 해제"
    )
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_secrets_cmd", "run_vib_secrets")
    )

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
    _ = p.add_argument(
        "file", nargs="?", default=None, help="특정 파일만 설명 (안 써도 돼요)"
    )
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    _ = p.add_argument("--ai", action="store_true", help="AI가 더 자세하게 분석")
    _ = p.add_argument(
        "--since-minutes",
        type=int,
        default=120,
        help="최근 몇 분 동안의 변경 (기본: 120분)",
    )
    _ = p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_explain_cmd", "run_vib_explain")
    )

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
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    _ = p.add_argument("--strict", action="store_true", help="더 꼼꼼하게 검사")
    _ = p.add_argument(
        "--since-minutes",
        type=int,
        default=120,
        help="최근 몇 분 동안의 변경 (기본: 120분)",
    )
    _ = p.add_argument("--write-report", action="store_true", help="결과를 파일로 저장")
    p.set_defaults(func=run_vib_guard)

    p = sub.add_parser(
        "claude-hook",
        help="Claude PreToolUse hook 상태를 관리해요",
        description="Claude 프로젝트의 PreToolUse hook 설치 상태와 on/off를 관리해요.",
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib claude-hook status\n"
            "  vib claude-hook enable\n"
            "  vib claude-hook disable"
        ),
    )
    _ = p.add_argument(
        "action",
        nargs="?",
        default="status",
        choices=["enable", "disable", "status"],
        help="실행할 동작",
    )
    p.set_defaults(
        func=lazy_command(
            "vibelign.commands.vib_claude_hook_cmd", "run_vib_claude_hook"
        )
    )

    p = sub.add_parser("pre-check", help=argparse.SUPPRESS)
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_precheck_cmd", "run_vib_precheck")
    )

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
    _ = p.add_argument(
        "tool",
        choices=["claude", "opencode", "cursor", "antigravity", "codex"],
        help="AI 도구 이름",
    )
    p.set_defaults(func=lazy_command("vibelign.commands.export_cmd", "run_export"))

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
    _ = p.add_argument(
        "--auto", action="store_true", help="앵커 자동 삽입 (추천만 볼 때는 생략)"
    )
    p.set_defaults(func=lazy_command("vibelign.commands.vib_scan_cmd", "run_vib_scan"))

    p = sub.add_parser(
        "show",
        help="앵커 블록만 콘솔에 찍어요",
        description=(
            "지정한 파일에서 앵커(_START~_END) 영역만 줄번호와 함께 출력해요.\n"
            "큰 파일의 일부만 확인할 때 Read 보다 정확하고 토큰 절약에 좋아요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib show vibelign/core/anchor_tools.py EXTRACT_ANCHOR_SPANS\n"
            "  vib show vibelign-gui/src/pages/Onboarding.tsx ONBOARDING"
        ),
    )
    _ = p.add_argument("file", help="파일 경로 (프로젝트 루트 기준)")
    _ = p.add_argument("anchor", help="앵커 이름 (_START/_END 없이)")
    p.set_defaults(func=lazy_command("vibelign.commands.vib_show_cmd", "run_vib_show"))

    p = sub.add_parser(
        "plan-structure",
        help="AI가 코딩하기 전 구조 계획을 만들어요",
        description=(
            "기능 설명을 바탕으로 어느 파일을 수정하고 어떤 파일을 새로 만들지 계획해요.\n"
            "생성된 계획은 .vibelign/plans/ 아래에 저장돼요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            '  vib plan-structure "OAuth 인증 추가"\n'
            '  vib plan-structure --scope vibelign/core/ "watch 기능 확장"\n'
            '  vib plan-structure --ai "mcp handler 수정"'
        ),
    )
    _ = p.add_argument("feature", nargs="+", help="구조 계획을 만들 기능 설명")
    _ = p.add_argument(
        "--ai", action="store_true", help="향후 AI 모드용 plan metadata로 기록"
    )
    _ = p.add_argument(
        "--scope",
        default="",
        help="분석 대상을 특정 경로로 좁혀요 (예: vibelign/core/)",
    )
    _ = p.add_argument(
        "--json", action="store_true", help="구조 계획 결과를 JSON으로 출력해요"
    )
    p.set_defaults(
        func=lazy_command(
            "vibelign.commands.vib_plan_structure_cmd", "run_vib_plan_structure"
        )
    )

    p = sub.add_parser(
        "transfer",
        help="AI 툴 바꿔도 맥락 유지 (PROJECT_CONTEXT.md 생성)",
        description=(
            "Claude Code → Cursor → Windsurf 등 AI 툴을 바꿀 때\n"
            "프로젝트 맥락을 한 파일로 정리해서 즉시 이어서 작업 가능하게 해요.\n"
            "PROJECT_CONTEXT.md 파일을 프로젝트 루트에 생성/갱신해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib transfer                       기본 생성\n"
            "  vib transfer --compact             경량 버전 (토큰 절약)\n"
            "  vib transfer --full                핵심 파일 전체 포함\n"
            "  vib transfer --handoff             AI 전환용 Session Handoff 블록 포함\n"
            "  vib transfer --handoff --print     Handoff 요약을 콘솔에도 출력\n"
            "  vib transfer --handoff --no-prompt 프롬프트 없이 자동 생성\n"
            "  vib transfer --out ctx.md          파일명 지정\n"
            "\n"
            "주의: --handoff와 --compact/--full은 함께 쓸 수 없습니다."
        ),
    )
    _ = p.add_argument("--compact", action="store_true", help="경량 버전 (토큰 최소화)")
    _ = p.add_argument("--full", action="store_true", help="핵심 파일 전체 포함")
    _ = p.add_argument(
        "--handoff", action="store_true", help="AI 전환용 Session Handoff 블록 포함"
    )
    _ = p.add_argument(
        "--print",
        dest="print_mode",
        action="store_true",
        help="Handoff 요약을 콘솔에 출력 (--handoff 전용)",
    )
    _ = p.add_argument(
        "--no-prompt",
        dest="no_prompt",
        action="store_true",
        help="프롬프트 없이 자동 생성 (--handoff 전용)",
    )
    _ = p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="파일 저장 없이 handoff 내용 미리 보기",
    )
    _ = p.add_argument(
        "--out", default=None, help="출력 파일명 (기본: PROJECT_CONTEXT.md)"
    )
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_transfer_cmd", "run_transfer")
    )

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
            "  vib watch --strict     꼼꼼 모드\n"
            "  vib watch --auto-fix   새 소스 파일에 앵커 자동 삽입"
        ),
    )
    _ = p.add_argument("--strict", action="store_true", help="더 꼼꼼하게 감시")
    _ = p.add_argument(
        "--auto-fix",
        action="store_true",
        help="새 소스 파일에 앵커가 없으면 자동으로 삽입",
    )
    _ = p.add_argument("--write-log", action="store_true", help="로그를 파일로 저장")
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    _ = p.add_argument(
        "--debounce-ms", type=int, default=800, help="감시 간격 (밀리초, 기본: 800)"
    )
    p.set_defaults(func=lazy_command("vibelign.commands.watch_cmd", "run_watch_cmd"))

    p = sub.add_parser(
        "bench",
        help="앵커 효과 검증 벤치마크",
        description=(
            "앵커가 AI 코드 수정 정확도를 높이는지 검증하는 벤치마크 도구예요.\n"
            "A(앵커 없음) vs B(앵커 있음) 조건으로 프롬프트를 생성하고,\n"
            "AI 수정 결과를 채점할 수 있어요. --patch 옵션은 별도의\n"
            "patch-suggester 정확도 회귀 테스트 (pinned-intent)를 돌려요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib bench --generate           A/B 프롬프트 생성\n"
            "  vib bench --score              AI 수정 결과 채점\n"
            "  vib bench --report             마크다운 리포트 생성\n"
            "  vib bench --patch              patch-suggester 정확도 측정\n"
            "  vib bench --patch --update-baseline  baseline 갱신"
        ),
    )
    _ = p.add_argument(
        "--generate", action="store_true", help="A/B 조건별 프롬프트 생성"
    )
    _ = p.add_argument("--score", action="store_true", help="AI 수정 결과 채점")
    _ = p.add_argument(
        "--report", action="store_true", help="마크다운 비교 리포트 생성"
    )
    _ = p.add_argument(
        "--patch",
        action="store_true",
        help="patch-suggester 정확도 회귀 측정 (pinned-intent sandbox)",
    )
    _ = p.add_argument(
        "--update-baseline",
        action="store_true",
        help="--patch 와 함께 사용, 현재 측정값으로 baseline 파일 덮어쓰기",
    )
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_bench_cmd", "run_vib_bench")
    )

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
    _ = p.add_argument(
        "command_name",
        nargs="?",
        default=None,
        help="상세히 볼 커맨드 이름 (예: checkpoint, anchor, guard ...)",
    )
    _ = p.add_argument("--all", action="store_true", help="전체 커맨드 상세 보기")
    _ = p.add_argument(
        "--save", action="store_true", help="VIBELIGN_MANUAL.md 파일로 저장"
    )
    _ = p.add_argument("--json", action="store_true", help="매뉴얼을 JSON으로 출력")
    p.set_defaults(func=_run_vib_manual)

    p = sub.add_parser(
        "rules",
        help="AI 개발 규칙 전체 보기 (vib manual rules 와 동일)",
        description="VibeLign이 AI한테 지키게 하는 모든 코딩 규칙을 보여줘요.",
    )
    p.set_defaults(func=_run_vib_rules)


# === ANCHOR: CLI_COMMAND_GROUPS_END ===
