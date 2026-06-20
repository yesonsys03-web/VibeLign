# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS_START ===
from __future__ import annotations

import argparse
import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vibelign.cli.cli_command_groups import SubparserFactory


# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS__RUN_VIB_MANUAL_START ===
def _run_vib_manual(args: object) -> None:
    run_vib_manual = cast(
        Callable[[object], None],
        importlib.import_module("vibelign.commands.vib_manual_cmd").run_vib_manual,
    )
    run_vib_manual(args)


# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS__RUN_VIB_MANUAL_END ===


# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS__RUN_VIB_RULES_START ===
def _run_vib_rules(_: object) -> None:
    run_vib_manual = cast(
        Callable[[object], None],
        importlib.import_module("vibelign.commands.vib_manual_cmd").run_vib_manual,
    )
    run_vib_manual(
        argparse.Namespace(command_name="rules", save=False, all=False, json=False)
    )


# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS__RUN_VIB_RULES_END ===


# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS_REGISTER_WORKFLOW_COMMAND_GROUP_START ===
def register_workflow_command_group(
    sub: SubparserFactory,
    lazy_command: Callable[[str, str], Callable[[object], None]],
) -> None:
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
            "  vib transfer --handoff --session-summary \"현재 세션 작업\" --first-next-action \"다음 할 일\"\n"
            "  vib transfer --handoff --verification \"pytest 통과\"\n"
            "  vib transfer --handoff --decision \"git 상태를 source of truth로 유지\"\n"
            "  vib transfer --handoff --ai --no-prompt   reviewable AI draft JSON 출력\n"
            "  vib transfer --handoff --dry-run   파일 저장 없이 미리 보기\n"
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
        "--ai", action="store_true", help="reviewable handoff draft JSON을 생성 (--handoff 전용)"
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
        "--session-summary",
        dest="session_summary",
        default=None,
        help="Session Handoff에 넣을 현재 세션 작업 요약 (--handoff 전용)",
    )
    _ = p.add_argument(
        "--first-next-action",
        dest="first_next_action",
        default=None,
        help="Session Handoff에 넣을 다음 AI의 첫 작업 (--handoff 전용)",
    )
    _ = p.add_argument(
        "--verification",
        dest="verification",
        action="append",
        default=None,
        help="Session Handoff에 넣을 검증 결과. 여러 번 지정 가능 (--handoff 전용)",
    )
    _ = p.add_argument(
        "--decision",
        dest="decision",
        action="append",
        default=None,
        help="work_memory decisions에 저장할 handoff 결정. 여러 번 지정 가능 (--handoff 전용)",
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
            "AI 수정 결과를 채점할 수 있어요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib bench --generate           A/B 프롬프트 생성\n"
            "  vib bench --score              AI 수정 결과 채점\n"
            "  vib bench --report             마크다운 리포트 생성"
        ),
    )
    _ = p.add_argument(
        "--generate", action="store_true", help="A/B 조건별 프롬프트 생성"
    )
    _ = p.add_argument("--score", action="store_true", help="AI 수정 결과 채점")
    _ = p.add_argument(
        "--report", action="store_true", help="마크다운 비교 리포트 생성"
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


# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS_REGISTER_WORKFLOW_COMMAND_GROUP_END ===
# === ANCHOR: CLI_WORKFLOW_COMMAND_GROUPS_END ===
