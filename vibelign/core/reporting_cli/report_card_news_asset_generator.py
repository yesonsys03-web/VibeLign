# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR_START ===
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
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
_ASSET_TIMEOUT_SECONDS: Final = 120
_BATCH_TIMEOUT_SECONDS: Final = 180
_JSON_OBJECT_RE: Final[re.Pattern[str]] = re.compile(r"\{[\s\S]*\}")


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
    if len(cards) > 1 and _shared_cli_provider(cards) is not None:
        return _materialize_via_batch(context, asset_dir, cards)
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
        svg = asset_path.read_text(encoding="utf-8")
        return _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))
    asset_dir.mkdir(parents=True, exist_ok=True)
    svg = _asset_svg(context, card)
    _ = asset_path.write_text(svg, encoding="utf-8")
    return _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SHARED_CLI_PROVIDER_START ===
def _shared_cli_provider(cards: list[VisualCardDict]) -> str | None:
    providers = {card["image"]["provider"] for card in cards}
    if len(providers) != 1:
        return None
    provider = next(iter(providers))
    return provider if provider in _CLI_ASSET_PROVIDERS else None
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SHARED_CLI_PROVIDER_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__MATERIALIZE_VIA_BATCH_START ===
def _materialize_via_batch(
    context: _AssetRenderContext,
    asset_dir: Path,
    cards: list[VisualCardDict],
) -> list[VisualCardDict]:
    resolved: dict[int, VisualCardDict] = {}
    pending: list[tuple[int, VisualCardDict, Path]] = []
    for index, card in enumerate(cards, 1):
        if card["image"]["asset_path"].strip():
            resolved[index] = card
            continue
        asset_relative = _asset_relative_path(context.slug, card, index)
        existing = context.root / asset_relative
        if existing.exists():
            svg = existing.read_text(encoding="utf-8")
            resolved[index] = _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))
            continue
        pending.append((index, card, asset_relative))
    if pending:
        asset_dir.mkdir(parents=True, exist_ok=True)
        svgs = _batch_svg_list(context, [card for _, card, _ in pending])
        for offset, (index, card, asset_relative) in enumerate(pending):
            svg = svgs[offset] if offset < len(svgs) and svgs[offset] is not None else _fallback_asset_svg(card)
            _ = (context.root / asset_relative).write_text(svg, encoding="utf-8")
            resolved[index] = _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))
    return [resolved[index] for index in range(1, len(cards) + 1)]
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__MATERIALIZE_VIA_BATCH_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_LIST_START ===
def _batch_svg_list(context: _AssetRenderContext, cards: list[VisualCardDict]) -> list[str | None]:
    provider = cards[0]["image"]["provider"]
    command = cli_adapters.build_cli_command(provider, _batch_svg_prompt(cards))
    if command is None:
        raise CardNewsAssetError(f"{provider} CLI를 찾지 못해 카드뉴스 이미지를 만들지 못했어요.")
    runner = context.runner or cli_adapters.SubprocessPlanningCliRunner()
    result = runner.run(command, cwd=context.root, input_text="", timeout_seconds=_BATCH_TIMEOUT_SECONDS)
    status = safe_planning_status(result.status, result.stdout)
    if status == "timeout":
        return [None] * len(cards)
    if status != "ok":
        raise CardNewsAssetError(f"{provider} CLI 카드뉴스 이미지 생성 실패: {result.stderr.strip() or status}")
    return _parse_batch_svgs(result.stdout, len(cards))
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_LIST_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__PARSE_BATCH_SVGS_START ===
def _parse_batch_svgs(stdout: str, count: int) -> list[str | None]:
    match = _JSON_OBJECT_RE.search(stdout.strip())
    if match is None:
        return [None] * count
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [None] * count
    raw = data.get("svgs") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return [None] * count
    out: list[str | None] = []
    for index in range(count):
        item = raw[index] if index < len(raw) and isinstance(raw[index], str) else ""
        try:
            svg = _extract_safe_svg(item)
        except CardNewsAssetError:
            svg = None
        out.append(_with_svg_schema(svg) if svg else None)
    return out
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__PARSE_BATCH_SVGS_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_PROMPT_START ===
def _batch_svg_prompt(cards: list[VisualCardDict]) -> str:
    lines: list[str] = []
    for index, card in enumerate(cards, 1):
        visual = (card["visual_prompt"] or card["image"]["prompt"])[:_VISUAL_PROMPT_LIMIT]
        lines.append(f'{index}. title="{card["title"]}" meaning="{card["body"][:160]}" visual="{visual}"')
    listing = "\n".join(lines)
    return (
        f"Create {len(cards)} rich, detailed SVG illustrations for report card body slots.\n"
        'Return ONLY one JSON object: {"svgs": ["<svg>...</svg>", ...]} with exactly one <svg> per card, in order.\n'
        "Each SVG: viewBox 0 0 320 150, hand-drawn editorial card-news style, bold black outlines,\n"
        "layered filled shapes, soft shadows, a clear focal scene (not a flat icon).\n"
        "No readable text, no Korean text, no Latin text, no <text>, no scripts, no external images, no URLs, no hrefs, no event handlers.\n"
        "Make each illustration specific to its card.\n\n"
        f"Cards:\n{listing}"
    )
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_PROMPT_END ===


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
        "Create one rich, detailed standalone SVG illustration for a report card body image slot.\n"
        "Return only one <svg>...</svg> element. No markdown fences, no explanation.\n"
        "Canvas: viewBox 0 0 320 150. Hand-drawn editorial card-news style with bold black outlines.\n"
        "Make it visually rich: layered shapes, filled areas, soft shadows, and a clear focal scene\n"
        "so it reads like an illustrator drew it, not a flat icon.\n"
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


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_SOURCE_START ===
def _asset_source(provider: str, svg_text: str) -> str:
    if provider not in _CLI_ASSET_PROVIDERS:
        return "template"
    return "fallback" if "data-sketch-symbols" in svg_text else "llm"
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_SOURCE_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__CARD_WITH_ASSET_START ===
def _card_with_asset(card: VisualCardDict, asset_relative: Path, source: str) -> VisualCardDict:
    prompt = card["visual_prompt"] or card["image"]["prompt"]
    image: VisualImageMetadata = {
        "provider": card["image"]["provider"],
        "asset_path": asset_relative.as_posix(),
        "prompt": prompt,
        "generated": True,
        "source": source if source in ("llm", "fallback", "template") else "template",
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
