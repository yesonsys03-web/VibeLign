# === ANCHOR: VIB_REPORT_RUNTIME_START ===
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, NotRequired, Protocol, TypedDict

from vibelign.commands.vib_report_context import ReportArgs, ReportCommandContext, read_report_context
from vibelign.commands.vib_report_render_payload import (
    RenderPayloadFormatError,
    load_render_payload_models_from_env,
)
from vibelign.core.reporting_cli import (
    ReportModel,
    ReportRendererUnavailable,
)
from vibelign.core.reporting_cli.polish_cache import load_polish_cache, polish_cache_key, save_polish_cache
from vibelign.core.reporting_cli.render_job import render_and_write
from vibelign.core.reporting_cli.report_card_news_asset_generator import CardNewsAssetError, materialize_card_news_assets
from vibelign.core.reporting_cli.report_visual_cards import VisualCardsDict, build_report_visual_cards
from vibelign.core.reporting_cli.report_visual_cards_cli import CliVisualCardsProvider, VisualCardsCliError
from vibelign.core.reporting_cli.storage import _report_slug

if TYPE_CHECKING:
    from vibelign.core.reporting_cli.report_assist import AssistProvider


# === ANCHOR: VIB_REPORT_RUNTIME_TYPES_START ===
class ReportPolisher(Protocol):
    def __call__(self, model: ReportModel, *, provider: str, root: Path) -> ReportModel:
        ...


class ReportRenderJsonPayload(TypedDict):
    ok: bool
    path: str
    report_type: str
    visual_cards: NotRequired[VisualCardsDict]
    card_news_poster: NotRequired[dict[str, str]]
# === ANCHOR: VIB_REPORT_RUNTIME_TYPES_END ===


# === ANCHOR: VIB_REPORT_RUNTIME_RUN_START ===
def run_report_command(raw: ReportArgs, polish_model: ReportPolisher) -> None:
    ctx = read_report_context(raw, _fail)
    if getattr(raw, "assist_missing", False):
        _print_assistance(raw, ctx)
        return
    if getattr(raw, "emit_model", False):
        _print_emit_model(raw, ctx)
        return
    if getattr(raw, "reject_blocks", None) is not None:
        _render_reject_blocks(raw, ctx)
        return
    model = _final_model(raw, ctx, polish_model)
    dest = _render_model(raw, ctx, model)
    _print_render_response(raw, ctx, model, dest)
# === ANCHOR: VIB_REPORT_RUNTIME_RUN_END ===


# === ANCHOR: VIB_REPORT_RUNTIME_MODES_START ===
def _print_assistance(raw: ReportArgs, ctx: ReportCommandContext) -> None:
    from vibelign.core.reporting_cli.report_assist import generate_report_assistance
    from vibelign.core.reporting_cli.report_quality import analyze_report_quality, quality_to_dict

    provider = _assist_provider(ctx.provider, ctx.root)
    assistance = generate_report_assistance(
        ctx.text,
        raw.type,
        date=ctx.report_date,
        author=ctx.author,
        provider=provider,
    )
    quality = quality_to_dict(analyze_report_quality(ctx.data, ctx.model, raw.type))
    print(
        json.dumps(
            {
                "ok": True,
                "report_type": raw.type,
                "quality": quality,
                "assistance": assistance,
            },
            ensure_ascii=False,
        )
    )


def _assist_provider(provider_name: str, root: Path) -> AssistProvider | None:
    if provider_name in ("", "auto", "local"):
        return None
    from vibelign.core.reporting_cli.report_assist_cli import CliAssistProvider

    return CliAssistProvider(provider_name, root=root)


def _print_emit_model(raw: ReportArgs, ctx: ReportCommandContext) -> None:
    from vibelign.core.reporting_cli.emit import emit_report_payload

    try:
        payload = emit_report_payload(
            str(ctx.plan_path),
            raw.type,
            date=ctx.report_date,
            polish=getattr(raw, "polish", False),
            provider=ctx.provider,
            root=ctx.root,
            author=ctx.author,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _fail(ctx.want_json, f"보고서 모델 생성 실패: {exc}")
    print(json.dumps(payload, ensure_ascii=False))


def _render_reject_blocks(raw: ReportArgs, ctx: ReportCommandContext) -> None:
    from vibelign.core.reporting_cli.merge import merge_models

    reject = _reject_blocks(raw.reject_blocks, ctx.want_json)
    base, polished = _render_payload_models(raw, ctx)
    merged = merge_models(base, polished, reject)
    dest = _render_model(raw, ctx, merged)
    _print_saved_report(ctx.want_json, dest, merged.report_type)


def _reject_blocks(reject_raw: str | None, want_json: bool) -> list[tuple[int, int]]:
    try:
        return [(int(section), int(block)) for section, block in json.loads(reject_raw or "[]")]
    except (ValueError, TypeError):
        _fail(want_json, "reject-blocks JSON 형식이 잘못됐어요: [[section,block],...]")


def _render_payload_models(raw: ReportArgs, ctx: ReportCommandContext) -> tuple[ReportModel, ReportModel]:
    polish_key = getattr(raw, "polish_key", None)
    try:
        payload_models = load_render_payload_models_from_env(polish_key)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RenderPayloadFormatError) as exc:
        _fail(ctx.want_json, f"render payload 형식이 잘못됐어요: {exc}")
    if payload_models is not None:
        return payload_models.base, payload_models.polished
    if not polish_key:
        _fail(ctx.want_json, "polish-key 가 필요해요(emit 응답의 key 값).")
    polished = load_polish_cache(ctx.root, _report_slug(ctx.slug_source), key=polish_key)
    if polished is None:
        _fail(ctx.want_json, "검토 결과가 만료됐어요. 보고서를 다시 생성해주세요.")
    return ctx.model, polished
# === ANCHOR: VIB_REPORT_RUNTIME_MODES_END ===


# === ANCHOR: VIB_REPORT_RUNTIME_RENDER_START ===
def _final_model(
    raw: ReportArgs,
    ctx: ReportCommandContext,
    polish_model: ReportPolisher,
) -> ReportModel:
    if not getattr(raw, "polish", False):
        return ctx.model
    key = polish_cache_key(ctx.model, provider=ctx.provider)
    slug = _report_slug(ctx.slug_source)
    cached = load_polish_cache(ctx.root, slug, key=key)
    if cached is not None:
        return cached
    model = polish_model(ctx.model, provider=ctx.provider, root=ctx.root)
    save_polish_cache(ctx.root, slug, key=key, model=model)
    return model


def _render_model(raw: ReportArgs, ctx: ReportCommandContext, model: ReportModel) -> Path:
    try:
        return render_and_write(
            ctx.root,
            model,
            getattr(raw, "format", "html") or "html",
            slug_source=ctx.slug_source,
            output=raw.output,
            force=raw.force,
            theme=ctx.report_theme,
            page_numbers=bool(getattr(raw, "page_numbers", True)),
            font_sizes=ctx.font_sizes,
            fonts=ctx.report_fonts,
        )
    except ReportRendererUnavailable as exc:
        _fail(ctx.want_json, str(exc))
    except (FileExistsError, ValueError) as exc:
        _fail(ctx.want_json, str(exc))


def _print_render_response(raw: ReportArgs, ctx: ReportCommandContext, model: ReportModel, dest: Path) -> None:
    if ctx.want_json:
        payload: ReportRenderJsonPayload = {
            "ok": True,
            "path": str(dest),
            "report_type": model.report_type,
        }
        if getattr(raw, "visual_cards", False):
            try:
                cards_payload = _visual_cards(raw, ctx, model)
                payload["visual_cards"] = cards_payload
                poster = _card_news_poster(raw, ctx, cards_payload)
                if poster is not None:
                    payload["card_news_poster"] = poster
            except (CardNewsAssetError, VisualCardsCliError) as exc:
                _fail(ctx.want_json, str(exc))
        print(json.dumps(payload, ensure_ascii=False))
        return
    _print_saved_report(False, dest, model.report_type)


def _print_saved_report(want_json: bool, dest: Path, report_type: str) -> None:
    if want_json:
        print(json.dumps({"ok": True, "path": str(dest), "report_type": report_type}, ensure_ascii=False))
        return
    from vibelign.terminal_render import clack_intro, clack_success

    clack_intro("VibeLign 보고서")
    clack_success(f"보고서 저장: {dest}")


def _emit_card_progress(stage: str) -> None:
    _ = sys.stderr.write(f"[progress] step=report-cards stage={stage}\n")
    sys.stderr.flush()


def _emit_card_news_event(kind: str, **fields: object) -> None:
    # Sketch-first progressive rendering: stream the draft cards / placeholder poster to the
    # GUI on stderr as a single compact JSON line so it can show an instant preview before the
    # slow LLM stages finish. Distinct from the [progress] bar lines; the Rust bridge parses
    # `{"type":"card_news_event",...}` and forwards it as a progress event.
    payload = {"type": "card_news_event", "kind": kind, **fields}
    _ = sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stderr.flush()


def _visual_cards(raw: ReportArgs, ctx: ReportCommandContext, model: ReportModel) -> VisualCardsDict:
    provider_name = getattr(raw, "visual_card_cli", "local") or "local"
    _emit_card_progress("draft")
    base = build_report_visual_cards(model, source_text=ctx.text)
    if provider_name in {"", "local"}:
        return base
    provider = CliVisualCardsProvider(provider_name, root=ctx.root)
    try:
        draft = provider.draft(base, ctx.text)
    except VisualCardsCliError:
        # The model's text rewrite is non-deterministic and occasionally returns unparseable
        # output. Degrade to the deterministic base cards instead of hard-failing the whole
        # card-news generation (poster mode still designs its poster from these cards).
        return base
    # Sketch-first: hand the storyboard to the GUI now so it can render instant sketch cards
    # while the slow asset/poster stage runs. Draft cards carry empty asset_path → sketches.
    _emit_card_news_event("draft", visual_cards=draft)
    _emit_card_progress("assets")
    # Poster mode redraws every card from text (title/body/caption) and never consumes the
    # per-card SVG assets: the LLM poster prompt takes only text, and the deterministic
    # fallback clears asset_path to re-render sketches. Generating the per-card SVGs here is
    # a wasted ~300s LLM batch, so skip it — the poster output is identical either way.
    if getattr(raw, "card_news_mode", "per-card") == "poster":
        return draft
    slug = _report_slug(ctx.slug_source)
    cards = materialize_card_news_assets(ctx.root, slug, draft["cards"])
    return {**draft, "cards": cards, "assets": [card["image"] for card in cards]}


def _card_news_poster(
    raw: ReportArgs, ctx: ReportCommandContext, cards_payload: VisualCardsDict
) -> dict[str, str] | None:
    if getattr(raw, "card_news_mode", "per-card") != "poster":
        return None
    provider_name = getattr(raw, "visual_card_cli", "local") or "local"
    if provider_name in {"", "local"} or cards_payload["status"] != "ready":
        return None
    from vibelign.core.reporting_cli.report_card_news_poster import (
        CardNewsPosterError,
        deterministic_poster_html,
        generate_card_news_poster,
    )

    _emit_card_progress("poster")
    # Sketch-first: show the deterministic placeholder poster immediately so the user is not
    # staring at a blank ≤300s wait; the GUI swaps it for the finished LLM poster on resolve.
    _emit_card_news_event(
        "poster_draft", html=deterministic_poster_html(cards_payload, cards_payload["cards"], ctx.root)
    )
    try:
        result = generate_card_news_poster(cards_payload, cards_payload["cards"], ctx.root, provider_name)
    except CardNewsPosterError as exc:
        _fail(ctx.want_json, str(exc))
    return {"html": result.html, "source": result.source}
# === ANCHOR: VIB_REPORT_RUNTIME_RENDER_END ===


# === ANCHOR: VIB_REPORT_RUNTIME_FAIL_START ===
def _fail(want_json: bool, message: str) -> NoReturn:
    if want_json:
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    else:
        print(message, file=sys.stderr)
    raise SystemExit(1)
# === ANCHOR: VIB_REPORT_RUNTIME_FAIL_END ===
# === ANCHOR: VIB_REPORT_RUNTIME_END ===
