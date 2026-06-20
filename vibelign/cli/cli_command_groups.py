# === ANCHOR: CLI_COMMAND_GROUPS_START ===
from __future__ import annotations

import argparse
import importlib
from collections.abc import Callable
from typing import Protocol, cast

from vibelign.cli.cli_report_command_groups import register_report_command_group
from vibelign.cli.cli_workflow_command_groups import register_workflow_command_group


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


# === ANCHOR: CLI_COMMAND_GROUPS__RUN_VIB_MCP_START ===
def _run_vib_mcp(_: object) -> None:
    # Why: GUI 번들에서 `vib mcp` 한 진입점으로 MCP 서버를 띄울 수 있게 한다.
    #      Claude Code/Cursor 등 외부 도구는 별도 `vibelign-mcp` 바이너리 없이
    #      `vib` 절대경로 + `mcp` 인자만으로 동일 서버에 도달.
    main = cast(
        Callable[[], None],
        importlib.import_module("vibelign.mcp.mcp_server").main,
    )
    main()


# === ANCHOR: CLI_COMMAND_GROUPS__RUN_VIB_MCP_END ===


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
            "API 키 설정(인터랙티브), 앵커 AI 보강, 커밋 후 자동 백업 on/off를 함께 관리해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib config                               API 키 설정 (인터랙티브)\n"
            "  vib config --ai-enhance status           AI 앵커 보강 상태 조회\n"
            "  vib config --ai-enhance enable           AI 앵커 보강 켜기\n"
            "  vib config --ai-enhance disable          AI 앵커 보강 끄기\n"
            "  vib config auto-backup status            커밋 후 자동 백업 상태 조회\n"
            "  vib config auto-backup on|off            커밋 후 자동 백업 켜기/끄기"
        ),
    )
    _ = p.add_argument(
        "--ai-enhance",
        dest="ai_enhance",
        choices=["enable", "disable", "status"],
        default=None,
        help="앵커 AI intent 자동 보강 on/off 토글 (.vibelign/config.yaml)",
    )
    _ = p.add_argument(
        "config_args",
        nargs="*",
        help=argparse.SUPPRESS,
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
    _ = p.add_argument(
        "--fix-anchors",
        action="store_true",
        help="앵커 없는 파일만 명시적으로 자동 정리",
    )
    _ = p.add_argument("--dry-run", action="store_true", help="수정 없이 대상만 미리 보기")
    _ = p.add_argument(
        "--paths",
        nargs="+",
        default=None,
        help="특정 파일만 대상으로 실행",
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
            "  vib anchor --auto --paths src/app.py                 특정 파일만 앵커 삽입\n"
            "  vib anchor --auto --module-only --paths src/app.py   파일 전체 앵커만 삽입\n"
            "  vib anchor --auto-intent                            AI가 모든 앵커 intent 자동 생성\n"
            "  vib anchor --validate                               앵커 검증\n"
            '  vib anchor --set-intent ANCHOR_NAME --intent "설명"  앵커 의도 직접 등록\n'
            "  vib anchor --list-intent                            등록된 의도 목록 보기"
        ),
    )
    _ = p.add_argument("--suggest", action="store_true", help="앵커 추천 받기")
    _ = p.add_argument("--auto", action="store_true", help="자동으로 앵커 삽입")
    _ = p.add_argument(
        "--module-only",
        action="store_true",
        help="고급: 함수/클래스 단위 대신 파일 전체 앵커만 삽입",
    )
    _ = p.add_argument(
        "--paths",
        nargs="+",
        default=None,
        help="특정 파일만 대상으로 실행 (예: --paths src/app.py tests/test_app.py)",
    )
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

    # === ANCHOR: CLI_COMMAND_GROUPS__RECOVER_COMMAND_START ===
    p = sub.add_parser(
        "recover",
        help="AI가 망가뜨린 변경을 읽기 전용으로 진단해요",
        description=(
            "현재 변경 상태를 보고 안전한 복구 방향을 설명해요.\n"
            "Phase 1에서는 파일을 수정하지 않습니다."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib recover --explain    복구 옵션 설명\n"
            "  vib recover --preview    복구 옵션 미리보기\n"
            "  vib recover --recommend --phrase 'GUI broke 30m ago'    복구 후보 추천 JSON\n"
            "  vib recover --file src/app.py    파일 복구 대상 미리보기\n"
            "  vib recover --file src/app.py --apply --checkpoint-id ckpt --sandwich-checkpoint-id safety --confirmation 'APPLY ckpt'"
        ),
    )
    _ = p.add_argument("--explain", action="store_true", help="복구 옵션을 설명")
    _ = p.add_argument("--preview", action="store_true", help="복구 옵션을 미리보기")
    _ = p.add_argument("--recommend", action="store_true", help="복구 후보 추천을 JSON으로 출력")
    _ = p.add_argument("--phrase", default="", help="복구 요청 문구")
    _ = p.add_argument("--file", default=None, help="복구 대상으로 검토할 파일")
    _ = p.add_argument("--json", action="store_true", help="복구 계획을 JSON으로 출력")
    _ = p.add_argument("--apply", action="store_true", help="명시 확인된 파일 복구를 실행")
    _ = p.add_argument("--checkpoint-id", default="", help="복구할 원본 체크포인트 ID")
    _ = p.add_argument("--sandwich-checkpoint-id", default="", help="복구 직전 안전 체크포인트 ID")
    _ = p.add_argument("--confirmation", default="", help="명시 확인 문구: APPLY <checkpoint-id>")
    _ = p.add_argument("--plan-id", default=None, help="감사 로그에 연결할 recovery plan ID")
    _ = p.add_argument("--candidate-id", default=None, help="감사 로그에 연결할 추천 candidate ID")
    _ = p.add_argument("--option-id", default=None, help="감사 로그에 연결할 recovery option ID")
    _ = p.add_argument("--recommendation-provider", default=None, help="감사 로그에 연결할 추천 provider")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_recover_cmd", "run_vib_recover")
    )
    # === ANCHOR: CLI_COMMAND_GROUPS__RECOVER_COMMAND_END ===

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

    p = sub.add_parser("mcp", help=argparse.SUPPRESS)
    p.set_defaults(func=_run_vib_mcp)
    mcp_sub = p.add_subparsers(dest="mcp_action")
    grant = mcp_sub.add_parser("grant", help="MCP capability 권한을 기록합니다")
    _ = grant.add_argument("capability", help="권한을 줄 MCP capability 이름")
    _ = grant.add_argument("--tool", required=True, help="권한을 줄 AI tool 이름")
    grant.set_defaults(
        func=lazy_command("vibelign.commands.vib_mcp_cmd", "run_vib_mcp_command")
    )
    grants = mcp_sub.add_parser("grants", help="MCP capability 권한 목록을 봅니다")
    grants.set_defaults(
        func=lazy_command("vibelign.commands.vib_mcp_cmd", "run_vib_mcp_command")
    )
    revoke = mcp_sub.add_parser("revoke", help="MCP capability 권한을 제거합니다")
    _ = revoke.add_argument("capability", help="권한을 제거할 MCP capability 이름")
    _ = revoke.add_argument("--tool", required=True, help="권한을 제거할 AI tool 이름")
    revoke.set_defaults(
        func=lazy_command("vibelign.commands.vib_mcp_cmd", "run_vib_mcp_command")
    )

    p = sub.add_parser("log-gui-error", help=argparse.SUPPRESS)
    _ = p.add_argument("--batch", action="store_true", help=argparse.SUPPRESS)
    _ = p.add_argument("--root", default="", help=argparse.SUPPRESS)
    p.set_defaults(
        func=lazy_command(
            "vibelign.commands.vib_log_gui_error_cmd", "run_vib_log_gui_error"
        )
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
        "_internal_record_commit",
        help=argparse.SUPPRESS,  # 사용자에게 숨김
        description="post-commit 훅이 호출. stdin 으로 commit 메시지 받음.",
    )
    _ = p.add_argument("sha", help="git commit SHA")
    p.set_defaults(
        func=lazy_command(
            "vibelign.commands.internal_record_commit_cmd",
            "run_internal_record_commit",
        )
    )

    p = sub.add_parser(
        "_internal_post_commit",
        help=argparse.SUPPRESS,
        description="post-commit 훅 내부 처리. stdin 으로 commit 메시지 받음.",
    )
    _ = p.add_argument("sha", help="git commit SHA")
    p.set_defaults(
        func=lazy_command(
            "vibelign.commands.internal_post_commit_cmd",
            "run_internal_post_commit",
        )
    )

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
        "memory",
        help="AI 작업 메모리를 확인하고 명시적으로 갱신해요",
        description=(
            "현재 작업 의도, 결정, 관련 파일, 검증 상태를 짧게 확인해요.\n"
            "decide/relevant 는 사용자가 직접 입력한 내용만 저장합니다."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib memory show\n"
            "  vib memory show --json\n"
            "  vib memory review\n"
            "  vib memory intent \"현재 목표\"\n"
            "  vib memory decide \"현재 목표\"\n"
            "  vib memory next \"다음 할 일\"\n"
            "  vib memory relevant src/app.py \"핵심 파일\"\n"
            "  vib memory proposal-create --session-summary \"현재 작업\" --first-next-action \"다음 할 일\"\n"
            "  vib memory proposal-create --relevant-file src/app.py::핵심 --verification \"pytest 통과\"\n"
            "  vib memory proposal-accept --field next_action --draft-json '{...}'\n"
            "  vib memory proposal-dismiss --field next_action --draft-json '{...}'\n"
            "  vib memory proposal-undo --proposal-hash abc123\n"
            "\n"
            "자주 쓰는 옵션:\n"
            "  show --json                         앱/자동화가 읽기 좋은 JSON으로 보기\n"
            "  proposal-create --session-summary    handoff 요약 제안\n"
            "  proposal-create --first-next-action  다음 할 일 제안\n"
            "  proposal-create --relevant-file      관련 파일 제안 (path::why)\n"
            "  proposal-create --verification       검증 기록 제안\n"
            "  proposal-create --risk-note          주의할 점 제안\n"
            "  proposal-accept --field --draft-json 수락해서 work_memory.json에 저장\n"
            "  proposal-dismiss --field --draft-json 거절하고 원본 메모리는 유지"
        ),
    )
    memory_sub = p.add_subparsers(
        dest="memory_action",
        required=True,
        metavar="{show,review,intent,decide,next,relevant,proposal-create,proposal-accept,proposal-dismiss,proposal-undo}",
    )
    p_show = memory_sub.add_parser("show", help="저장된 메모리를 보여줘요")
    _ = p_show.add_argument("--json", action="store_true", help="메모리 상태를 JSON으로 출력")
    p_show.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_show")
    )
    p_review = memory_sub.add_parser("review", help="handoff 전에 확인할 메모리를 검토해요")
    p_review.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_review")
    )
    p_intent = memory_sub.add_parser("intent", help="현재 목표를 명시적으로 확정해요")
    _ = p_intent.add_argument("intent", nargs="+", help="확정할 현재 목표")
    p_intent.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_intent")
    )
    p_decide = memory_sub.add_parser("decide", help="중요한 결정을 명시적으로 저장해요")
    _ = p_decide.add_argument("decision", nargs="+", help="저장할 결정 문장")
    p_decide.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_decide")
    )
    p_next = memory_sub.add_parser("next", help="다음 작업을 명시적으로 저장해요")
    _ = p_next.add_argument("next_action", nargs="+", help="저장할 다음 작업")
    p_next.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_next")
    )
    p_relevant = memory_sub.add_parser("relevant", help="관련 파일을 명시적으로 저장해요")
    _ = p_relevant.add_argument("path", help="프로젝트 상대 파일 경로")
    _ = p_relevant.add_argument("why", nargs="+", help="왜 중요한지")
    p_relevant.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_relevant")
    )
    p_create = memory_sub.add_parser("proposal-create", help="reviewable handoff proposal draft를 만들어요")
    _ = p_create.add_argument("--session-summary", default="", help="제안에 사용할 handoff 요약")
    _ = p_create.add_argument("--first-next-action", default="", help="제안에 사용할 다음 작업")
    _ = p_create.add_argument("--relevant-file", action="append", default=None, help="제안할 관련 파일: path::why")
    _ = p_create.add_argument("--verification", action="append", default=None, help="제안할 검증 기록")
    _ = p_create.add_argument("--risk-note", action="append", default=None, help="제안할 위험/주의 메모")
    p_create.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_proposal_create")
    )
    p_accept = memory_sub.add_parser("proposal-accept", help="reviewed handoff proposal 필드를 수락해요")
    _ = p_accept.add_argument("--draft-json", required=True, help="handoff draft JSON")
    _ = p_accept.add_argument("--field", required=True, help="수락할 필드 이름")
    p_accept.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_proposal_accept")
    )
    p_dismiss = memory_sub.add_parser("proposal-dismiss", help="handoff proposal 필드를 거절해요")
    _ = p_dismiss.add_argument("--draft-json", required=True, help="handoff draft JSON")
    _ = p_dismiss.add_argument("--field", required=True, help="거절할 필드 이름")
    p_dismiss.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_proposal_dismiss")
    )
    p_undo = memory_sub.add_parser("proposal-undo", help="최근 수락한 proposal을 되돌려요")
    _ = p_undo.add_argument("--proposal-hash", required=True, help="되돌릴 proposal hash")
    p_undo.set_defaults(
        func=lazy_command("vibelign.commands.vib_memory_cmd", "run_vib_memory_proposal_undo")
    )

    register_report_command_group(sub, lazy_command)
    register_workflow_command_group(sub, lazy_command)


# === ANCHOR: CLI_COMMAND_GROUPS_END ===
