# === ANCHOR: VIB_REPORT_CMD_START ===
from __future__ import annotations

import json
import sys
from datetime import date as _date
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.project_root import resolve_project_root
from vibelign.core.reporting_cli import (
    ReportRendererUnavailable,
    build_doc_report_model,
    build_report_model,
    parse_plan_markdown,
    polish_report_model,
)
from vibelign.core.reporting_cli.font_sizes import normalize_report_font_sizes
from vibelign.core.reporting_cli.render_job import render_and_write
from vibelign.core.reporting_cli.polish_cache import (
    load_polish_cache,
    polish_cache_key,
    save_polish_cache,
)
from vibelign.core.reporting_cli.storage import _report_slug
from vibelign.core.reporting_cli.themes import has_theme
from vibelign.terminal_render import clack_intro, clack_success


# === ANCHOR: VIB_REPORT_CMD_REPORTARGS_START ===
class ReportArgs(Protocol):
    plan: str
    type: str
    format: str
    output: str | None
    force: bool
    date: str | None
    json: bool
    polish: bool
    cli: str
    emit_model: bool
    reject_blocks: str | None
    polish_key: str | None
    theme: str
    title_font_size: int | None
    heading_font_size: int | None
    body_font_size: int | None
    meta_font_size: int | None
    author: str
    page_numbers: bool
# === ANCHOR: VIB_REPORT_CMD_REPORTARGS_END ===


# === ANCHOR: VIB_REPORT_CMD_RUN_VIB_REPORT_START ===
def run_vib_report(args: object) -> None:
    raw = cast(ReportArgs, args)
    want_json = bool(raw.json)
    report_date = raw.date or _date.today().isoformat()

    plan_path = Path(raw.plan).expanduser()
    if not plan_path.exists():
        _fail(want_json, f"기획안 파일을 찾을 수 없어요: {plan_path}")
        return

    root = resolve_project_root(Path.cwd())
    author = getattr(raw, "author", "") or ""
    report_theme = getattr(raw, "theme", "classic") or "classic"
    if not has_theme(report_theme):
        _fail(want_json, f"알 수 없는 디자인 테마예요: {report_theme}")
        return
    try:
        font_sizes = normalize_report_font_sizes(
            title=getattr(raw, "title_font_size", None),
            heading=getattr(raw, "heading_font_size", None),
            body=getattr(raw, "body_font_size", None),
            meta=getattr(raw, "meta_font_size", None),
        )
    except ValueError as exc:
        _fail(want_json, str(exc))
        return
    try:
        text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(want_json, f"기획안을 읽을 수 없어요: {exc}")
        return

    if raw.type == "doc":
        model = build_doc_report_model(
            text,
            date=report_date,
            source_plan_path=str(plan_path),
            author=author,
            default_title=plan_path.stem,
        )
        if not model.sections:
            _fail(want_json, "문서에 내보낼 내용이 없습니다.")
            return
        slug_source = model.title or plan_path.stem
    else:
        try:
            data = parse_plan_markdown(text)
            model = build_report_model(
                data,
                raw.type,
                date=report_date,
                source_plan_path=str(plan_path),
                author=author,
            )
        except ValueError as exc:
            _fail(want_json, str(exc))
            return
        slug_source = data.title or data.idea or plan_path.stem
    provider = getattr(raw, "cli", "auto") or "auto"

    # --emit-model: 렌더·저장 없이 base/polished 구조화 모델 + key 를 JSON 으로 반환한다.
    if getattr(raw, "emit_model", False):
        from vibelign.core.reporting_cli.emit import emit_report_payload

        try:
            payload = emit_report_payload(
                str(plan_path), raw.type, date=report_date,
                polish=getattr(raw, "polish", False), provider=provider, root=root,
                author=getattr(raw, "author", "") or "",
            )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            _fail(want_json, f"보고서 모델 생성 실패: {exc}")
            return
        print(json.dumps(payload, ensure_ascii=False))
        return

    # --reject-blocks: 거부 인덱스 + emit 이 준 --polish-key 로 캐시된 polished 를 로드해 병합·렌더.
    # 캐시 미스 시 조용히 재-polish 하지 않고 명시 에러로 실패한다 → "검토한 내용 = 저장된 내용" 보장.
    reject_raw = getattr(raw, "reject_blocks", None)
    if reject_raw is not None:
        from vibelign.core.reporting_cli.merge import merge_models

        try:
            reject = [(int(s), int(b)) for s, b in json.loads(reject_raw)]
        except (ValueError, TypeError):
            _fail(want_json, "reject-blocks JSON 형식이 잘못됐어요: [[section,block],...]")
            return
        polish_key = getattr(raw, "polish_key", None)
        if not polish_key:
            _fail(want_json, "polish-key 가 필요해요(emit 응답의 key 값).")
            return
        slug = _report_slug(slug_source)
        polished = load_polish_cache(root, slug, key=polish_key)
        if polished is None:
            _fail(want_json, "검토 결과가 만료됐어요. 보고서를 다시 생성해주세요.")
            return
        try:
            merged = merge_models(model, polished, reject)
            fmt = getattr(raw, "format", "html") or "html"
            dest = render_and_write(
                root, merged, fmt, slug_source=slug_source, output=raw.output, force=raw.force,
                theme=report_theme,
                page_numbers=bool(getattr(raw, "page_numbers", True)),
                font_sizes=font_sizes,
            )
        except ReportRendererUnavailable as exc:
            _fail(want_json, str(exc))
            return
        except (FileExistsError, ValueError) as exc:
            _fail(want_json, str(exc))
            return
        if want_json:
            print(json.dumps({"ok": True, "path": str(dest), "report_type": merged.report_type}, ensure_ascii=False))
        else:
            clack_intro("VibeLign 보고서")
            clack_success(f"보고서 저장: {dest}")
        return

    if getattr(raw, "polish", False):
        provider = getattr(raw, "cli", "auto") or "auto"
        # enrich 캐시(§6): 동일 입력 재요청 시 provider 재호출 0.
        key = polish_cache_key(model, provider=provider)
        slug = _report_slug(slug_source)
        cached = load_polish_cache(root, slug, key=key)
        if cached is not None:
            model = cached
        else:
            model = polish_report_model(model, provider=provider, root=root)
            save_polish_cache(root, slug, key=key, model=model)

    fmt = getattr(raw, "format", "html") or "html"
    try:
        dest = render_and_write(
            root, model, fmt, slug_source=slug_source, output=raw.output, force=raw.force,
            theme=report_theme,
            page_numbers=bool(getattr(raw, "page_numbers", True)),
            font_sizes=font_sizes,
        )
    except ReportRendererUnavailable as exc:
        _fail(want_json, str(exc))
        return
    except (FileExistsError, ValueError) as exc:
        _fail(want_json, str(exc))
        return

    if want_json:
        print(
            json.dumps(
                {"ok": True, "path": str(dest), "report_type": model.report_type},
                ensure_ascii=False,
            )
        )
    else:
        clack_intro("VibeLign 보고서")
        clack_success(f"보고서 저장: {dest}")
# === ANCHOR: VIB_REPORT_CMD_RUN_VIB_REPORT_END ===


# === ANCHOR: VIB_REPORT_CMD__FAIL_START ===
def _fail(want_json: bool, message: str) -> None:
    if want_json:
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    else:
        print(message, file=sys.stderr)
    raise SystemExit(1)
# === ANCHOR: VIB_REPORT_CMD__FAIL_END ===
# === ANCHOR: VIB_REPORT_CMD_END ===
