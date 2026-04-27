# === ANCHOR: CLI_CORE_COMMANDS_START ===
import argparse
from collections.abc import Callable
from typing import Protocol


# === ANCHOR: CLI_CORE_COMMANDS_SUBPARSERFACTORY_START ===
class SubparserFactory(Protocol):
    # === ANCHOR: CLI_CORE_COMMANDS_ADD_PARSER_START ===
    def add_parser(
        self,
        name: str,
        *,
        help: str | None = None,
        description: str | None = None,
        epilog: str | None = None,
        **kwargs: object,
        # === ANCHOR: CLI_CORE_COMMANDS_SUBPARSERFACTORY_END ===
        # === ANCHOR: CLI_CORE_COMMANDS_ADD_PARSER_END ===
    ) -> argparse.ArgumentParser: ...


# === ANCHOR: CLI_CORE_COMMANDS_REGISTER_CORE_COMMANDS_START ===
def register_core_commands(
    sub: SubparserFactory,
    lazy_command: Callable[[str, str], Callable[[object], None]],
    run_init: Callable[[object], None],
    # === ANCHOR: CLI_CORE_COMMANDS_REGISTER_CORE_COMMANDS_END ===
) -> None:
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
    p.set_defaults(
        func=lazy_command("vibelign.commands.install_guide_cmd", "run_install_guide")
    )

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
    _ = p.add_argument("--force", action="store_true", help="강제로 다시 설치")
    p.set_defaults(func=run_init)

    p = sub.add_parser(
        "start",
        help="안심하고 바이브코딩 시작!",
        description=(
            "안심하고 바이브코딩을 시작하세요!\n"
            "AI한테 코딩을 시키기 전에, 이 명령어로 안전하게 준비해요.\n"
            "AGENTS.md, AI_DEV_SYSTEM_SINGLE_FILE.md 등 필요한 파일을 자동으로 만들어요.\n"
            "--all-tools를 쓰면 Claude, Antigravity, OpenCode, Cursor, Codex 준비도 한 번에 해줘요.\n"
            "기본값은 기존 설정을 보존하고, --force일 때만 VibeLign 설정을 다시 만들거나 덮어써요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib start   새 프로젝트 또는 VibeLign 처음 사용하는 프로젝트 세팅\n"
            "  vib start --all-tools   여러 AI 도구를 한 번에 준비\n"
            "  vib start --all-tools --force   기존 VibeLign 설정도 다시 생성\n"
            "\n"
            "VibeLign 자체를 재설치하려면:\n"
            "  vib init"
        ),
    )
    group = p.add_mutually_exclusive_group()
    _ = group.add_argument(
        "--all-tools",
        action="store_true",
        help="Claude, Antigravity, OpenCode, Cursor, Codex 설정을 한 번에 준비해요",
    )
    _ = group.add_argument(
        "--tools",
        help="설정할 도구 목록 (예: claude,opencode,cursor,antigravity 또는 codex)",
    )
    _ = p.add_argument(
        "--force",
        action="store_true",
        help="기존 VibeLign 설정 파일도 다시 생성하거나 덮어써요",
    )
    _ = p.add_argument(
        "--quickstart", action="store_true", help="start + anchor를 한 번에 실행해요"
    )
    _ = p.add_argument("message", nargs="*", help="저장할 메시지 (안 써도 돼요)")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_start_cmd", "run_vib_start")
    )

    p = sub.add_parser(
        "checkpoint",
        help="게임 세이브처럼 지금 상태를 저장해요",
        description=(
            "현재 프로젝트 상태를 세이브 포인트로 저장해요.\n"
            "AI가 뭔가 망가뜨려도 이 지점으로 되돌릴 수 있어요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib checkpoint              빠르게 저장\n"
            '  vib checkpoint "로그인 완성"  메시지와 함께 저장'
        ),
    )
    _ = p.add_argument(
        "message", nargs="*", help="저장할 메시지 (안 써도 돼요) / 'list'로 목록 조회"
    )
    _ = p.add_argument("--json", action="store_true", help="결과를 JSON으로 반환")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_checkpoint_cmd", "run_vib_checkpoint")
    )

    p = sub.add_parser(
        "undo",
        help="저장한 곳으로 되돌려요",
        description=(
            "마지막 체크포인트로 되돌려요.\nAI가 코드를 망가뜨렸을 때 쓰세요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib undo                                마지막 저장으로 되돌리기\n"
            "  vib undo --list                         저장 목록 보기\n"
            "  vib undo --checkpoint-id <id> --force   ID로 바로 복원 (확인 생략)"
        ),
    )
    _ = p.add_argument("--list", action="store_true", help="체크포인트 목록 보기")
    _ = p.add_argument(
        "--checkpoint-id", metavar="ID", help="복원할 체크포인트 ID (GUI용)"
    )
    _ = p.add_argument("--force", action="store_true", help="확인 프롬프트 생략")
    _ = p.add_argument("--json", action="store_true", help="결과를 JSON으로 반환")
    p.set_defaults(func=lazy_command("vibelign.commands.vib_undo_cmd", "run_vib_undo"))

    p = sub.add_parser(
        "history",
        help="저장 목록을 봐요",
        description="지금까지 저장한 체크포인트 목록을 보여줘요.",
        epilog="이렇게 쓰세요:\n  vib history    저장 기록 보기",
    )
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_history_cmd", "run_vib_history")
    )

    p = sub.add_parser(
        "docs-build",
        help="docs visual cache를 수동으로 생성해요",
        description=(
            "watch가 꺼져 있어도 markdown 문서의 visual cache를 다시 만들어요.\n"
            "인자를 생략하면 전체 문서를, 경로를 주면 해당 문서만 다시 생성해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib docs-build\n"
            "  vib docs-build PROJECT_CONTEXT.md\n"
            "  vib docs-build docs/wiki/index.md --json"
        ),
    )
    _ = p.add_argument("path", nargs="?", help="다시 생성할 단일 markdown 경로")
    _ = p.add_argument("--json", action="store_true", help="결과를 JSON으로 출력")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_docs_build_cmd", "run_vib_docs_build")
    )

    p = sub.add_parser(
        "docs-enhance",
        help="AI 로 현재 문서의 요약 필드를 생성해요 (ANTHROPIC_API_KEY 필요)",
        description=(
            "기존 artifact 의 ai_fields 를 LLM 호출로 덮어써요.\n"
            "먼저 `vib docs-build <path>` 를 실행해 artifact 가 있어야 해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib docs-enhance docs/wiki/index.md\n"
            "  vib docs-enhance PROJECT_CONTEXT.md --json"
        ),
    )
    _ = p.add_argument("path", nargs="?", help="enhance 대상 markdown 경로")
    _ = p.add_argument("--json", action="store_true", help="결과를 JSON으로 출력")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_docs_build_cmd", "run_vib_docs_enhance")
    )

    p = sub.add_parser(
        "docs-index",
        help="docs viewer용 문서 인덱스를 JSON으로 출력해요 (GUI/Tauri 전용)",
        description=(
            "docs viewer가 사용하는 문서 인덱스를 JSON으로 출력해요.\n"
            "vib 자체에 vibelign 모듈이 포함돼 있어 별도 Python 환경이 없어도 동작해요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib docs-index\n"
            "  vib docs-index /path/to/project\n"
            "  vib docs-index --visual-contract"
        ),
    )
    _ = p.add_argument("path", nargs="?", help="인덱스를 만들 프로젝트 루트 (생략 시 현재 위치)")
    _ = p.add_argument(
        "--visual-contract",
        action="store_true",
        help="docs visual artifact contract와 예시 스키마를 JSON으로 출력",
    )
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_docs_build_cmd", "run_vib_docs_index")
    )

    # doc-sources sub-subcommand: add / remove / list
    p = sub.add_parser(
        "doc-sources",
        help="추가 문서 소스를 등록/제거/조회해요 (GUI 전용)",
        description=(
            "추가 문서 소스(.omc/plans 등)를 등록/제거/조회해요.\n"
            "등록된 소스는 docs viewer 사이드바에 Custom 카테고리로 표시됩니다."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib doc-sources list\n"
            "  vib doc-sources add .omc/plans\n"
            "  vib doc-sources remove .omc/plans"
        ),
    )
    doc_sources_sub = p.add_subparsers(
        dest="doc_sources_action",
        required=True,
        metavar="{list,add,remove}",
    )

    p_list = doc_sources_sub.add_parser("list", help="등록된 추가 문서 소스 목록을 JSON으로 출력해요")
    p_list.set_defaults(
        func=lazy_command("vibelign.commands.vib_doc_sources_cmd", "run_vib_doc_sources_list")
    )

    p_add = doc_sources_sub.add_parser("add", help="추가 문서 소스를 등록해요")
    _ = p_add.add_argument("path", help="등록할 문서 소스 경로 (프로젝트 루트 기준 상대 경로)")
    p_add.set_defaults(
        func=lazy_command("vibelign.commands.vib_doc_sources_cmd", "run_vib_doc_sources_add")
    )

    p_remove = doc_sources_sub.add_parser("remove", help="추가 문서 소스를 제거해요")
    _ = p_remove.add_argument("path", help="제거할 문서 소스 경로")
    p_remove.set_defaults(
        func=lazy_command("vibelign.commands.vib_doc_sources_cmd", "run_vib_doc_sources_remove")
    )


# === ANCHOR: CLI_CORE_COMMANDS_END ===
