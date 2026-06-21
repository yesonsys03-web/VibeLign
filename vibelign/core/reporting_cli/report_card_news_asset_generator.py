# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR_START ===
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import re
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Final

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.storage import safe_plan_slug
from vibelign.core.planning_cli.response_policy import safe_planning_status
from vibelign.core.reporting_cli.report_card_news_sketch import render_card_sketch_svg
from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict, VisualImageMetadata

_ASSET_SCHEMA_VERSION = "report-card-news-svg-asset-v1"
_MAX_ASSET_STEM_CHARS = 56
_CLI_ASSET_PROVIDERS: Final = frozenset({"claude", "codex", "agy", "opencode"})
_SVG_RE: Final[re.Pattern[str]] = re.compile(r"<svg\b[\s\S]*?</svg>", re.IGNORECASE)
_FORBIDDEN_SVG_RE: Final[re.Pattern[str]] = re.compile(r"<\s*(script|foreignObject)\b", re.IGNORECASE)
_TEXT_ELEMENT_RE: Final[re.Pattern[str]] = re.compile(r"<text\b[\s\S]*?</text>", re.IGNORECASE)
_UNSAFE_ATTR_RE: Final[re.Pattern[str]] = re.compile(r"""\s(?:on[a-z]+|href|xlink:href)\s*=\s*("[^"]*"|'[^']*')""", re.IGNORECASE)
_SVG_SCHEMA_ATTR: Final = f'data-schema="{_ASSET_SCHEMA_VERSION}"'
_VISUAL_PROMPT_LIMIT: Final = 900
_MAX_CONCURRENT_ASSET_REQUESTS: Final = 3
_ASSET_TIMEOUT_SECONDS: Final = 90


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR_CARDNEWSASSETERROR_START ===
class CardNewsAssetError(ValueError):
    pass
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR_CARDNEWSASSETERROR_END ===


@dataclass(frozen=True, slots=True)
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSETRENDERCONTEXT_START ===
class _AssetRenderContext:
    root: Path
    slug: str
    runner: cli_adapters.PlanningCliRunner | None
    timeout_seconds: int
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSETRENDERCONTEXT_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR_MATERIALIZE_CARD_NEWS_ASSETS_START ===
def materialize_card_news_assets(
    root: Path,
    slug: str,
    cards: list[VisualCardDict],
    runner: cli_adapters.PlanningCliRunner | None = None,
    timeout_seconds: int = _ASSET_TIMEOUT_SECONDS,
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR_MATERIALIZE_CARD_NEWS_ASSETS_END ===
) -> list[VisualCardDict]:
    context = _AssetRenderContext(root=root, slug=slug, runner=runner, timeout_seconds=timeout_seconds)
    asset_dir = _safe_asset_dir(root, slug)
    if len(cards) <= 1:
        return [_materialize_card_asset(context, asset_dir, index, card) for index, card in enumerate(cards, 1)]
    worker_count = min(_MAX_CONCURRENT_ASSET_REQUESTS, len(cards))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(_materialize_card_asset, context, asset_dir, index, card)
            for index, card in enumerate(cards, 1)
        ]
        return [future.result() for future in futures]


def _materialize_card_asset(
    context: _AssetRenderContext,
    asset_dir: Path,
    index: int,
    card: VisualCardDict,
) -> VisualCardDict:
    if card["image"]["asset_path"].strip():
        return card
    asset_relative = _asset_relative_path(context.slug, card, index)
    asset_path = context.root / asset_relative
    if asset_path.exists():
        return _card_with_asset(card, asset_relative)
    asset_dir.mkdir(parents=True, exist_ok=True)
    _ = asset_path.write_text(_asset_svg(context, card), encoding="utf-8")
    return _card_with_asset(card, asset_relative)


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SAFE_ASSET_DIR_START ===
def _safe_asset_dir(root: Path, slug: str) -> Path:
    asset_dir = root / ".vibelign" / "reports" / "card-news" / "assets" / f"{slug}-card-news"
    _assert_inside_root(root, asset_dir)
    return asset_dir
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SAFE_ASSET_DIR_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSERT_INSIDE_ROOT_START ===
def _assert_inside_root(root: Path, path: Path) -> None:
    try:
        _ = path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise CardNewsAssetError("카드뉴스 이미지 asset 경로가 프로젝트 밖을 가리켜요.") from exc
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSERT_INSIDE_ROOT_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_RELATIVE_PATH_START ===
def _asset_relative_path(slug: str, card: VisualCardDict, index: int) -> Path:
    stem_source = card["title"] or card["id"] or f"card-{index}"
    stem = safe_plan_slug(stem_source)[:_MAX_ASSET_STEM_CHARS].strip(" .-") or f"card-{index}"
    digest = sha1(_asset_digest_source(card).encode("utf-8")).hexdigest()[:10]
    return Path(".vibelign") / "reports" / "card-news" / "assets" / f"{slug}-card-news" / f"{index:02d}-{stem}-{digest}.svg"
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_RELATIVE_PATH_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_DIGEST_SOURCE_START ===
def _asset_digest_source(card: VisualCardDict) -> str:
    return "\n".join((card["id"], card["title"], card["body"], card["visual_prompt"], card["image"]["prompt"]))
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_DIGEST_SOURCE_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_SVG_START ===
def _asset_svg(context: _AssetRenderContext, card: VisualCardDict) -> str:
    provider = card["image"]["provider"]
    if provider in _CLI_ASSET_PROVIDERS:
        return _llm_asset_svg(context, card, provider)
    return _fallback_asset_svg(card)
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_SVG_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__FALLBACK_ASSET_SVG_START ===
def _fallback_asset_svg(card: VisualCardDict) -> str:
    return (
        render_card_sketch_svg(card).replace(
            "<svg ",
            f'<svg xmlns="http://www.w3.org/2000/svg" data-schema="{_ASSET_SCHEMA_VERSION}" ',
            1,
        )
        + "\n"
    )
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__FALLBACK_ASSET_SVG_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__LLM_ASSET_SVG_START ===
def _llm_asset_svg(context: _AssetRenderContext, card: VisualCardDict, provider: str) -> str:
    command = cli_adapters.build_cli_command(provider, _svg_prompt(card))
    if command is None:
        raise CardNewsAssetError(f"{provider} CLI를 찾지 못해 카드뉴스 이미지를 만들지 못했어요.")
    runner = context.runner or cli_adapters.SubprocessPlanningCliRunner()
    result = runner.run(command, cwd=context.root, input_text="", timeout_seconds=context.timeout_seconds)
    status = safe_planning_status(result.status, result.stdout)
    if status == "timeout":
        return _fallback_asset_svg(card)
    if status != "ok":
        raise CardNewsAssetError(f"{provider} CLI 카드뉴스 이미지 생성 실패: {result.stderr.strip() or status}")
    svg = _extract_safe_svg(result.stdout)
    if svg is None:
        return _fallback_asset_svg(card)
    return _with_svg_schema(svg)
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__LLM_ASSET_SVG_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SVG_PROMPT_START ===
def _svg_prompt(card: VisualCardDict) -> str:
    visual_prompt = (card["visual_prompt"] or card["image"]["prompt"])[:_VISUAL_PROMPT_LIMIT]
    return (
        "Create one standalone SVG illustration for a report card body image slot.\n"
        "Return only one <svg>...</svg> element. No markdown fences, no explanation.\n"
        "Canvas: viewBox 0 0 320 150. Use a hand-drawn educational card-news style with bold black outlines.\n"
        "Keep the SVG simple, under 80 elements, and use geometric shapes only.\n"
        "Do not include readable text, Korean text, Latin text, <text>, scripts, external images, URLs, hrefs, or event handlers.\n"
        "Make the illustration specific to this visual prompt, not generic.\n\n"
        f"Card title: {card['title']}\n"
        f"Card body meaning: {card['body'][:260]}\n"
        f"Visual prompt: {visual_prompt}\n"
        f"Negative prompt: {card['negative_prompt'][:260]}"
    )
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SVG_PROMPT_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__EXTRACT_SAFE_SVG_START ===
def _extract_safe_svg(stdout: str) -> str | None:
    match = _SVG_RE.search(stdout.strip())
    if match is None:
        return None
    svg = _sanitize_svg(match.group(0).strip())
    if _FORBIDDEN_SVG_RE.search(svg) or _has_external_url(svg):
        raise CardNewsAssetError("CLI가 안전하지 않은 SVG 이미지를 반환했어요.")
    return svg
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__EXTRACT_SAFE_SVG_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SANITIZE_SVG_START ===
def _sanitize_svg(svg: str) -> str:
    without_text = _TEXT_ELEMENT_RE.sub("", svg)
    return _UNSAFE_ATTR_RE.sub("", without_text)
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SANITIZE_SVG_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__HAS_EXTERNAL_URL_START ===
def _has_external_url(svg: str) -> bool:
    allowed_namespaces = svg.replace("http://www.w3.org/2000/svg", "").replace("http://www.w3.org/1999/xlink", "")
    return "http://" in allowed_namespaces or "https://" in allowed_namespaces
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__HAS_EXTERNAL_URL_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__WITH_SVG_SCHEMA_START ===
def _with_svg_schema(svg: str) -> str:
    prepared = svg
    if "xmlns=" not in prepared[:160]:
        prepared = prepared.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    if _SVG_SCHEMA_ATTR not in prepared[:220]:
        prepared = prepared.replace("<svg ", f"<svg {_SVG_SCHEMA_ATTR} ", 1)
    return f"{prepared}\n"
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__WITH_SVG_SCHEMA_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__CARD_WITH_ASSET_START ===
def _card_with_asset(card: VisualCardDict, asset_relative: Path) -> VisualCardDict:
    prompt = card["visual_prompt"] or card["image"]["prompt"]
    image: VisualImageMetadata = {
        "provider": card["image"]["provider"],
        "asset_path": asset_relative.as_posix(),
        "prompt": prompt,
        "generated": True,
    }
    return {
        "id": card["id"],
        "title": card["title"],
        "body": card["body"],
        "caption": card["caption"],
        "visual_prompt": card["visual_prompt"],
        "negative_prompt": card["negative_prompt"],
        "source_refs": card["source_refs"],
        "image": image,
        "approved": card["approved"],
    }
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__CARD_WITH_ASSET_END ===
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR_END ===
