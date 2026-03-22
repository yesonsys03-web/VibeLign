from argparse import Namespace
from pathlib import Path

from vibelign.core.git_hooks import (
    install_pre_commit_secret_hook,
    uninstall_pre_commit_secret_hook,
)
from vibelign.core.secret_scan import SecretFinding, scan_staged_secrets
from vibelign.terminal_render import (
    clack_error,
    clack_info,
    clack_intro,
    clack_outro,
    clack_success,
    clack_warn,
)


def _print_findings(findings: list[SecretFinding]) -> None:
    for finding in findings:
        location = finding.path
        if finding.line_number is not None:
            location += f":{finding.line_number}"
        clack_warn(f"{location} [{finding.rule_id}] {finding.snippet}")


def run_vib_secrets(args: Namespace) -> None:
    root = Path.cwd()

    if getattr(args, "install_hook", False):
        result = install_pre_commit_secret_hook(root)
        if result.status == "not-git":
            clack_error("Git 저장소에서만 비밀정보 보호 훅을 설치할 수 있어요.")
            raise SystemExit(1)
        if result.status == "existing-hook":
            clack_warn("기존 pre-commit 훅이 있어서 덮어쓰지 않았어요.")
            clack_info(
                "기존 훅에 `vib secrets --staged` 한 줄을 추가하면 함께 쓸 수 있어요."
            )
            raise SystemExit(1)
        if result.status == "chmod-failed":
            clack_error("훅 파일은 만들었지만 실행 권한을 주지 못했어요.")
            if result.detail:
                clack_info(result.detail)
            raise SystemExit(1)
        clack_success("Git 커밋 비밀정보 보호 훅을 설치했어요.")
        if result.path is not None:
            clack_info(str(result.path))
        return

    if getattr(args, "uninstall_hook", False):
        result = uninstall_pre_commit_secret_hook(root)
        if result.status == "removed":
            clack_success("VibeLign 비밀정보 보호 훅을 제거했어요.")
            return
        if result.status == "chmod-failed":
            clack_warn("훅 권한 상태를 확인하지 못했어요.")
            raise SystemExit(1)
        if result.status == "foreign-hook":
            clack_warn("다른 pre-commit 훅은 건드리지 않았어요.")
            raise SystemExit(1)
        clack_warn("제거할 VibeLign 비밀정보 보호 훅이 없어요.")
        raise SystemExit(1)

    if not getattr(args, "staged", False):
        clack_intro("VibeLign 비밀정보 점검")
        clack_info("커밋 전에 검사하려면: vib secrets --staged")
        clack_info("훅 설치: vib secrets --install-hook")
        clack_outro("준비 완료")
        return

    try:
        result = scan_staged_secrets(root)
    except Exception as exc:
        clack_error(f"staged 변경사항을 검사하지 못했어요: {exc}")
        raise SystemExit(1) from exc

    if result.has_findings:
        clack_error("커밋에 비밀정보처럼 보이는 내용이 있어 차단했어요.")
        _print_findings(result.findings)
        clack_info("실제 키라면 삭제하거나 환경변수로 옮긴 뒤 다시 커밋하세요.")
        clack_info(
            "오탐이면 해당 줄에 `vibelign: allow-secret` 주석을 붙여 예외 처리할 수 있어요."
        )
        raise SystemExit(1)

    clack_success("staged 변경사항에서 비밀정보를 찾지 못했어요.")
