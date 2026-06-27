# === ANCHOR: CLI_REPORT_COMMAND_GROUPS_START ===
from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibelign.cli.cli_command_groups import SubparserFactory


# === ANCHOR: CLI_REPORT_COMMAND_GROUPS_REGISTER_REPORT_COMMAND_GROUP_START ===
def register_report_command_group(
    sub: SubparserFactory,
    lazy_command: Callable[[str, str], Callable[[argparse.Namespace], None]],
) -> None:
    p = sub.add_parser(
        "plan",
        help="기획안 만들기",
        description="아이디어를 결정론적 템플릿 기획안으로 정리해요.",
        epilog=(
            "이렇게 쓰세요:\n"
            '  vib plan "예약 앱 만들고 싶어" --template-only\n'
            '  vib plan "예약 앱 만들고 싶어" --template-only --json'
        ),
    )
    _ = p.add_argument("idea", nargs="*", help="기획할 아이디어")
    _ = p.add_argument(
        "--template-only",
        action="store_true",
        help="LLM 없이 템플릿 기획안만 생성해요",
    )
    _ = p.add_argument("--output", default=None, help="저장할 프로젝트 상대 경로")
    _ = p.add_argument("--append-to", default=None, help="기존 기획안 파일에 페르소나 응답 추가")
    _ = p.add_argument("--force", action="store_true", help="기존 output 파일 덮어쓰기")
    _ = p.add_argument("--language", default="auto", help="기획안 언어")
    _ = p.add_argument(
        "--cli",
        default="auto",
        help="기획 보강에 사용할 공식 CLI 또는 쉼표 목록",
    )
    _ = p.add_argument(
        "--agents",
        default=None,
        help="실행할 페르소나 목록 (예: chloe,gio,mina)",
    )
    _ = p.add_argument("--save-transcript", action="store_true", help="원문 응답 저장")
    _ = p.add_argument(
        "--llm-timeout-seconds",
        type=int,
        default=300,
        help="CLI 응답 대기 시간",
    )
    _ = p.add_argument("--json", action="store_true", help="결과를 JSON으로 출력해요")
    p.set_defaults(func=lazy_command("vibelign.commands.vib_plan_cmd", "run_vib_plan"))

    r = sub.add_parser(
        "report",
        help="기획안을 보고서로 내보내기",
        description="기획안 마크다운을 업무/제안/결과 보고서 HTML 로 변환해요.",
        epilog=(
            "이렇게 쓰세요:\n"
            '  vib report plans/예약-앱.md --type work\n'
            '  vib report plans/예약-앱.md --type proposal --json'
        ),
    )
    _ = r.add_argument("plan", help="기획안 .md 경로")
    _ = r.add_argument(
        "--type",
        default="work",
        help="보고서 종류 (work=업무, proposal=제안, result=결과)",
    )
    _ = r.add_argument(
        "--format", default="html", choices=["html", "docx", "pptx"], help="출력 포맷"
    )
    _ = r.add_argument(
        "--output", default=None, help="저장 경로 (기본: .vibelign/reports/)"
    )
    _ = r.add_argument("--force", action="store_true", help="기존 --output 파일 덮어쓰기")
    _ = r.add_argument("--date", default=None, help="보고서 날짜 (기본: 오늘)")
    _ = r.add_argument("--json", action="store_true", help="JSON 으로 결과 출력")
    _ = r.add_argument("--polish", action="store_true", help="AI 로 어조 다듬기(무료 provider, 기본 OFF)")
    _ = r.add_argument("--cli", default="auto", choices=["auto", "codex", "opencode", "agy", "claude"], help="다듬기/보완 provider (claude 는 명시 opt-in)")
    _ = r.add_argument("--emit-model", action="store_true", help="다듬기 전/후 구조화 모델을 JSON 으로 출력(파일 미저장)")
    _ = r.add_argument("--assist-missing", action="store_true", help="부족한 보고서 항목 보완 후보를 JSON 으로 출력(파일 미저장)")
    _ = r.add_argument("--visual-cards", action="store_true", help="보고서용 카드뉴스 companion JSON 을 함께 출력")
    _ = r.add_argument(
        "--visual-card-cli",
        default="local",
        choices=["local", "codex", "opencode", "agy", "claude"],
        help="카드뉴스 초안 작성 provider (기본 local=규칙 기반)",
    )
    _ = r.add_argument(
        "--card-news-mode",
        default="per-card",
        choices=["per-card", "poster"],
        help="카드뉴스 생성 방식 (per-card=카드별 SVG, poster=CLI가 HTML 전체 디자인)",
    )
    _ = r.add_argument("--reject-blocks", default=None, help="원본 유지할 블록 인덱스 JSON: [[section,block],...]")
    _ = r.add_argument("--polish-key", default=None, help="emit 응답의 key — render 가 그 캐시 항목만 로드(재현성)")
    _ = r.add_argument("--theme", default="classic", metavar="THEME", help="디자인 테마 (기본 classic)")
    _ = r.add_argument("--title-font-size", type=int, default=None, metavar="PT", help="타이틀 폰트 크기")
    _ = r.add_argument("--heading-font-size", type=int, default=None, metavar="PT", help="헤드라인 폰트 크기")
    _ = r.add_argument("--body-font-size", type=int, default=None, metavar="PT", help="본문 폰트 크기")
    _ = r.add_argument("--meta-font-size", type=int, default=None, metavar="PT", help="머리말(종류·날짜·작성자) 폰트 크기")
    _ = r.add_argument("--heading-font", default=None, metavar="FONT", help="제목 폰트 ID")
    _ = r.add_argument("--body-font", default=None, metavar="FONT", help="본문 폰트 ID")
    _ = r.add_argument("--author", default="", help="작성자 이름 (메타에 표시)")
    _ = r.add_argument("--page-numbers", action=argparse.BooleanOptionalAction, default=True, help="페이지 번호(Word, 기본 ON)")
    r.set_defaults(
        func=lazy_command("vibelign.commands.vib_report_cmd", "run_vib_report")
    )

    sp = sub.add_parser("report-stamp-pdf", help="생성된 PDF 에 페이지 번호 스탬프")
    _ = sp.add_argument("pdf", help="대상 PDF 경로")
    _ = sp.add_argument("--json", action="store_true", help="JSON 으로 결과 출력")
    sp.set_defaults(
        func=lazy_command("vibelign.commands.vib_report_stamp_cmd", "run_vib_report_stamp")
    )

    cn = sub.add_parser(
        "report-card-news",
        help="승인된 보고서 카드뉴스를 HTML/JSON 결과물로 저장",
        description="카드뉴스 companion payload에서 승인된 카드만 확정 결과물로 저장해요.",
    )
    _ = cn.add_argument("payload", help="카드뉴스 companion JSON payload 경로")
    _ = cn.add_argument("--json", action="store_true", help="JSON 으로 결과 출력")
    cn.set_defaults(
        func=lazy_command("vibelign.commands.vib_report_card_news_cmd", "run_vib_report_card_news")
    )


# === ANCHOR: CLI_REPORT_COMMAND_GROUPS_REGISTER_REPORT_COMMAND_GROUP_END ===
# === ANCHOR: CLI_REPORT_COMMAND_GROUPS_END ===
