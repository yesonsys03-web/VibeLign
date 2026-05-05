# === ANCHOR: CLI_BASE_START ===
import argparse
import importlib
import sys
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from typing_extensions import override

from vibelign.terminal_render import print_cli_help

if TYPE_CHECKING:
    from _typeshed import SupportsWrite
else:
    _WriteT = TypeVar("_WriteT", contravariant=True)

    # === ANCHOR: CLI_BASE_SUPPORTSWRITE_START ===
    class SupportsWrite(Protocol[_WriteT]):
        # === ANCHOR: CLI_BASE_WRITE_START ===
        # === ANCHOR: CLI_BASE_SUPPORTSWRITE_END ===
        def write(self, s: _WriteT) -> object: ...

        # === ANCHOR: CLI_BASE_WRITE_END ===


# === ANCHOR: CLI_BASE_RICHARGUMENTPARSER_START ===
class RichArgumentParser(argparse.ArgumentParser):
    # === ANCHOR: CLI_BASE___INIT___START ===
    def __init__(
        self,
        prog: str | None = None,
        usage: str | None = None,
        description: str | None = None,
        epilog: str | None = None,
        parents: Sequence[argparse.ArgumentParser] = (),
        formatter_class: type[argparse.HelpFormatter] = argparse.HelpFormatter,
        prefix_chars: str = "-",
        fromfile_prefix_chars: str | None = None,
        argument_default: object | None = None,
        conflict_handler: str = "error",
        add_help: bool = True,
        allow_abbrev: bool = True,
        exit_on_error: bool = True,
        # === ANCHOR: CLI_BASE___INIT___END ===
    ) -> None:
        super().__init__(
            prog=prog,
            usage=usage,
            description=description,
            epilog=epilog,
            parents=parents,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            prefix_chars=prefix_chars,
            fromfile_prefix_chars=fromfile_prefix_chars,
            argument_default=argument_default,
            conflict_handler=conflict_handler,
            add_help=add_help,
            allow_abbrev=allow_abbrev,
            exit_on_error=exit_on_error,
        )

    @override
    # === ANCHOR: CLI_BASE__PRINT_MESSAGE_START ===
    def _print_message(
        self,
        message: str | None,
        file: SupportsWrite[str] | None = None,
        # === ANCHOR: CLI_BASE__PRINT_MESSAGE_END ===
    ) -> None:
        if not message:
            return
        # === ANCHOR: CLI_BASE_RICHARGUMENTPARSER_END ===
        if file not in (None, sys.stdout):
            _ = file.write(message)
            return
        print_cli_help(str(message))


MAIN_DESCRIPTION = """\
VibeLign - AI한테 코딩 시켜도 안전하게 지켜주는 도구

처음 시작:
  start       프로젝트 세팅 (AGENTS.md 등 필요 파일 자동 생성)
  init        VibeLign 소스 수정 후 재설치할 때 사용
  install     단계별 설치 방법 안내

세이브 & 되돌리기:
  checkpoint  게임 세이브처럼 지금 상태를 저장해요
  undo        저장한 곳으로 되돌려요
  history     저장 목록을 봐요
  recover     되돌리기 전에 안전한 복구 후보를 먼저 보여줘요
  backup-db-viewer       백업 DB 실제 사용량을 읽기 전용으로 확인해요
  backup-db-maintenance  백업 DB 파일 크기를 안전하게 점검/정리해요

점검 & 확인:
  doctor      프로젝트 건강 상태를 확인해요
  guard       AI가 코드를 망가뜨리지 않았는지 검사해요
  explain     뭐가 바뀌었는지 쉽게 알려줘요

AI 수정 요청:
 patch       말로 요청하면 안전한 수정 계획을 만들어요
  anchor      AI가 건드려도 되는 안전 구역을 표시해요
  scan        앵커 스캔 + 코드맵 갱신을 한 번에 해요
  plan-structure  코딩 전에 구조 계획을 만들어요
  claude-hook     Claude 저장 전 검사를 관리해요
  secrets         API 키 같은 비밀정보 커밋을 막아요

파일 & 설정:
  protect     중요한 파일을 잠가요
  transfer    AI 툴 전환 시 맥락 파일 생성
  memory      지금 하던 일과 다음 할 일을 세션 메모리에 저장해요
  ask         파일이 뭘 하는지 설명해줘요
  config      API 키 설정
  export      AI 도구용 설정 내보내기
  watch       실시간 감시
  bench       앵커 효과를 비교 실험해요

문서 보기 & 다시생성:
  docs-build    markdown 문서의 visual cache를 다시 만들어요
  docs-enhance  AI 로 현재 문서의 요약 필드를 생성해요
  docs-index    docs viewer가 쓰는 문서 목록/계약 정보를 보여줘요

도움말:
  manual      코알못을 위한 상세 사용 설명서
  rules       AI 개발 규칙 전체 보기
  completion  탭 자동완성 설정"""

MAIN_EPILOG = """\
처음이세요? 이것만 따라하세요:
  1. vib start              처음 한 번만!
  2. vib checkpoint "저장"  작업 전에 세이브
  3. vib doctor             상태 확인

자세한 사용법: vib <명령어> --help

설치: pip install vibelign  또는  uv tool install vibelign
자세한 설치 방법 (터미널 여는 법 + uv 설치 포함): vib install --help"""


# === ANCHOR: CLI_BASE_LAZY_COMMAND_START ===
def lazy_command(module_name: str, func_name: str) -> Callable[[object], object]:
    # === ANCHOR: CLI_BASE_RUNNER_START ===
    def runner(args: object) -> object:
        module = importlib.import_module(module_name)
        func = cast(Callable[[object], object], getattr(module, func_name))
        return func(args)

    # === ANCHOR: CLI_BASE_RUNNER_END ===
    # === ANCHOR: CLI_BASE_LAZY_COMMAND_END ===

    return runner


# === ANCHOR: CLI_BASE_END ===
