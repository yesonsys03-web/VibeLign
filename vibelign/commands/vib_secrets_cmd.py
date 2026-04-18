# === ANCHOR: VIB_SECRETS_CMD_START ===
from argparse import Namespace
from pathlib import Path

from vibelign.core.git_hooks import (
    install_pre_commit_secret_hook,
    uninstall_pre_commit_secret_hook,
)
from vibelign.core.project_root import resolve_project_root
from vibelign.core.secret_scan import (
    SecretFinding,
    scan_all_history,
    scan_staged_secrets,
)
from vibelign.terminal_render import (
    clack_error,
    clack_info,
    clack_intro,
    clack_outro,
    clack_success,
    clack_warn,
)


# === ANCHOR: VIB_SECRETS_CMD__PRINT_FINDINGS_START ===
def _print_findings(findings: list[SecretFinding]) -> None:
    for finding in findings:
        location = finding.path
        if finding.line_number is not None:
            location += f":{finding.line_number}"
        clack_warn(f"{location} [{finding.rule_id}] {finding.snippet}")


# === ANCHOR: VIB_SECRETS_CMD__PRINT_FINDINGS_END ===


# === ANCHOR: VIB_SECRETS_CMD_RUN_VIB_SECRETS_START ===
def run_vib_secrets(args: Namespace) -> None:
    root = resolve_project_root(Path.cwd())

    if getattr(args, "install_hook", False):
        result = install_pre_commit_secret_hook(root)
        if result.status == "not-git":
            clack_error("Git 저장소에서만 커밋 자동 검사를 켤 수 있어요.")
            raise SystemExit(1)
        if result.status == "existing-hook":
            clack_warn("이미 다른 커밋 자동 실행 설정이 있어서 덮어쓰지 않았어요.")
            clack_info(
                "그 설정 안에 `vib secrets --staged`와 `vib guard --strict`를 추가하면 같이 쓸 수 있어요."
            )
            raise SystemExit(1)
        if result.status == "chmod-failed":
            clack_error(
                "자동 검사 파일은 만들었지만 실행 가능하게 마무리하지 못했어요."
            )
            if result.detail:
                clack_info(result.detail)
            raise SystemExit(1)
        clack_success("이제부터 커밋할 때마다 비밀정보와 strict guard를 자동 검사해요.")
        if result.path is not None:
            clack_info(str(result.path))
        return

    if getattr(args, "uninstall_hook", False):
        result = uninstall_pre_commit_secret_hook(root)
        if result.status == "removed":
            clack_success("커밋할 때마다 돌던 자동 검사를 껐어요.")
            return
        if result.status == "chmod-failed":
            clack_warn("자동 검사 파일 상태를 끝까지 확인하지 못했어요.")
            raise SystemExit(1)
        if result.status == "foreign-hook":
            clack_warn("다른 자동 실행 설정은 건드리지 않았어요.")
            raise SystemExit(1)
        clack_warn("끄거나 지울 VibeLign 자동 검사가 없어요.")
        raise SystemExit(1)

    if getattr(args, "all", False):
        clack_intro("VibeLign 정밀검사 — 전체 히스토리")
        clack_info("규모에 따라 시간이 걸릴 수 있어요. 중단하려면 Ctrl-C")

        def _on_progress(done: int, total: int | None) -> None:
            if total is not None:
                clack_info(f"커밋 {done}/{total} 검사 중")
            else:
                clack_info(f"커밋 {done}개 검사 완료")

        try:
            history = scan_all_history(root, on_progress=_on_progress)
        except Exception as exc:
            clack_error(f"히스토리 검사 중 오류가 발생했어요: {exc}")
            raise SystemExit(1) from exc

        if history.has_findings:
            clack_error("과거 커밋에 비밀정보로 보이는 값이 남아있어요.")
            _print_findings(history.findings)
            clack_info(
                "키는 즉시 로테이션하세요. 이력 청소는 git filter-repo 또는 BFG를 사용하세요."
            )
            raise SystemExit(1)

        clack_success("전체 히스토리에서 비밀정보를 찾지 못했어요.")
        return

    if not getattr(args, "staged", False):
        clack_intro("VibeLign 비밀정보 점검")
        clack_info("지금 바로 검사하려면: vib secrets --staged")
        clack_info("전체 히스토리 정밀검사는: vib secrets --all")
        clack_info("앞으로 커밋할 때마다 자동 검사하려면: vib secrets --install-hook")
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


# === ANCHOR: VIB_SECRETS_CMD_RUN_VIB_SECRETS_END ===
# === ANCHOR: VIB_SECRETS_CMD_END ===
