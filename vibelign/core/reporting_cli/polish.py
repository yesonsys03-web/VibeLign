from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.response_policy import safe_planning_status
from vibelign.core.reporting_cli.models import Block, ReportModel, Section

# design §6: 무료 provider 전용. planning 의 provider_try_order 는 claude 를 포함하므로
# 재사용하지 않는다(비용 노출 방지). claude 는 명시 요청 시에만.
FREE_PROVIDERS: tuple[str, ...] = ("codex", "opencode", "agy")
_POLISH_BLOCK_KINDS = {"paragraph", "summary"}


def polish_try_order(provider: str | None) -> list[str]:
    """다듬기 provider 시도 순서. auto/None → 무료 전용. 명시 provider → 그것 우선 + 무료 보충.
    claude 는 provider 가 정확히 'claude' 일 때만 포함된다(자동 폴백으로는 절대 안 들어감)."""
    if not provider or provider == "auto":
        return list(FREE_PROVIDERS)
    order = [provider]
    for p in FREE_PROVIDERS:
        if p != provider:
            order.append(p)
    return order


def polish_block_text(
    text: str, *, provider: str, runner: cli_adapters.PlanningCliRunner, root: Path, timeout_seconds: int
) -> str | None:
    """텍스트 한 덩이를 비즈니스 보고 어조로 다듬는다. 실패 시 None."""
    if not text.strip():
        return None
    prompt = (
        "다음 보고서 문장을 비즈니스 보고 어조로 자연스럽게 다듬어줘. "
        "단, 숫자·비율·금액·날짜·고유명사는 절대 바꾸지 말고, 원문에 없는 사실이나 "
        "'대폭·획기적' 같은 과장 표현을 새로 만들지 마. 군더더기만 덜어내고 의미는 그대로 유지해. "
        "설명·따옴표 없이 다듬은 문장만 출력해.\n\n"
        f"{text}"
    )
    for adapter in polish_try_order(provider):
        # build_cli_command 가 실제 실행 명령(전체 경로 + 서브커맨드)을 만든다.
        # None = 미설치 → 다음 provider. 프로덕션 정확성을 위해 이 명령을 그대로 실행한다.
        command = cli_adapters.build_cli_command(adapter, prompt)
        if command is None:
            continue
        result = runner.run(command, cwd=root, input_text="", timeout_seconds=timeout_seconds)
        if safe_planning_status(result.status, result.stdout) == "ok":
            cleaned = result.stdout.strip()
            if cleaned:
                return cleaned
    return None


def polish_report_model(
    model: ReportModel,
    *,
    provider: str = "auto",
    runner=None,
    root: Path | None = None,
    timeout_seconds: int = 60,
) -> ReportModel:
    """ReportModel 의 paragraph/summary 블록 텍스트를 다듬은 새 ReportModel 을 반환한다.
    블록별 실패는 원문 유지(graceful). 입력 model 은 변경하지 않는다."""
    if runner is None:
        runner = cli_adapters.SubprocessPlanningCliRunner()
    if root is None:
        root = Path.cwd()

    new_sections: list[Section] = []
    for section in model.sections:
        new_blocks: list[Block] = []
        for block in section.blocks:
            if block.kind in _POLISH_BLOCK_KINDS and block.text:
                polished = polish_block_text(
                    block.text, provider=provider, runner=runner, root=root,
                    timeout_seconds=timeout_seconds,
                )
                new_blocks.append(replace(block, text=polished) if polished else block)
            else:
                new_blocks.append(block)
        new_sections.append(replace(section, blocks=new_blocks))
    return replace(model, sections=new_sections)
