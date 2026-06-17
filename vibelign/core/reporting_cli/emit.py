# === ANCHOR: REPORT_EMIT_START ===
from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli import (
    build_doc_report_model,
    build_report_model,
    parse_plan_markdown,
)
from vibelign.core.reporting_cli.model_json import model_to_dict
from vibelign.core.reporting_cli.polish import polish_report_model_with_guards
from vibelign.core.reporting_cli.polish_cache import polish_cache_key, save_polish_cache
from vibelign.core.reporting_cli.storage import _report_slug
from vibelign.core.reporting_cli.vague_lint import lint_model


def emit_report_payload(
    plan_path: str,
    report_type: str,
    *,
    date: str,
    polish: bool,
    provider: str,
    root: Path,
    author: str = "",
) -> dict:
    """base/polished 구조화 모델 + 캐시 key + guards/vague_warnings 를 조립한다.
    polish 시 결과를 polish 캐시에 저장해 render 단계가 같은 key 로 재사용하게 한다."""
    plan = Path(plan_path).expanduser()
    text = plan.read_text(encoding="utf-8")
    if report_type == "doc":
        base = build_doc_report_model(
            text, date=date, source_plan_path=str(plan), author=author, default_title=plan.stem
        )
        slug = _report_slug(base.title or plan.stem)
    else:
        data = parse_plan_markdown(text)
        base = build_report_model(data, report_type, date=date, source_plan_path=str(plan), author=author)
        slug = _report_slug(data.title or data.idea or plan.stem)

    # 캐시 키는 항상 계산해 payload 에 싣는다(render 가 이 key 로만 캐시를 로드 → 재현성 보장).
    key = polish_cache_key(base, provider=provider)
    guards: list[dict] = []
    if polish:
        polished, guards = polish_report_model_with_guards(base, provider=provider, root=root)
        save_polish_cache(root, slug, key=key, model=polished)
    else:
        polished = base
    vague_warnings = lint_model(polished)

    return {
        "ok": True,
        "report_type": report_type,
        "slug": slug,
        "key": key,
        "base": model_to_dict(base),
        "polished": model_to_dict(polished),
        "guards": guards,
        "vague_warnings": vague_warnings,
    }
# === ANCHOR: REPORT_EMIT_END ===
