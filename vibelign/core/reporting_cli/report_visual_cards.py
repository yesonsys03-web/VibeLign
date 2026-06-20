from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal, Protocol, TypedDict

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.reader import parse_generic_markdown

VISUAL_CARDS_SCHEMA_VERSION: Final = "report-visual-cards-v1"
NO_TEXT_PROMPT: Final = "no readable text in image"
DRAFT_PROVIDER_NAME: Final = "provider-neutral-draft"
_HANGUL_RE: Final[re.Pattern[str]] = re.compile(r"[가-힣]")
_MAX_CARDS: Final = 6
_MIN_CARDS: Final = 3
_SOURCE_SECTION_OFFSET: Final = 1000
_REQUIRED_CATEGORIES: Final = ("summary", "evidence", "decision", "risk", "next_action")
_CATEGORY_HEADINGS: Final[dict[str, str]] = {
    "리스크": "risk",
    "위험": "risk",
    "다음 액션": "next_action",
    "후속": "next_action",
    "확정된 결정": "decision",
    "결정": "decision",
    "근거": "evidence",
    "지표": "evidence",
    "요약": "summary",
    "개요": "summary",
    "목표": "summary",
}

VisualCardsStatus = Literal["ready", "empty"]
CardSeedCategory = Literal["summary", "evidence", "decision", "risk", "next_action", "context"]


class VisualCardSourceRef(TypedDict):
    source_plan_path: str
    section: int
    block: int
    heading: str


class VisualImageMetadata(TypedDict):
    provider: str
    asset_path: str
    prompt: str
    generated: bool


class VisualCardDict(TypedDict):
    id: str
    title: str
    body: str
    caption: str
    visual_prompt: str
    negative_prompt: str
    source_refs: list[VisualCardSourceRef]
    image: VisualImageMetadata
    approved: bool


class VisualCardsDict(TypedDict):
    schema_version: str
    status: VisualCardsStatus
    provider: str
    cards: list[VisualCardDict]
    assets: list[VisualImageMetadata]


@dataclass(frozen=True)
class VisualImageRequest:
    card_id: str
    visual_prompt: str
    negative_prompt: str


class VisualImageProvider(Protocol):
    provider_name: str

    def generate(self, request: VisualImageRequest) -> VisualImageMetadata:
        ...


@dataclass(frozen=True)
class _CardSeed:
    section_index: int
    block_index: int
    heading: str
    text: str
    category: CardSeedCategory


def build_report_visual_cards(
    model: ReportModel,
    provider: VisualImageProvider | None = None,
    source_text: str | None = None,
) -> VisualCardsDict:
    seeds = _card_seeds(model, source_text)
    provider_name = provider.provider_name if provider is not None else DRAFT_PROVIDER_NAME
    if not seeds:
        return {
            "schema_version": VISUAL_CARDS_SCHEMA_VERSION,
            "status": "empty",
            "provider": provider_name,
            "cards": [],
            "assets": [],
        }
    cards: list[VisualCardDict] = []
    for index, seed in enumerate(_bounded_seeds(seeds)):
        card_id = f"report-card-{index + 1}"
        visual_prompt = _visual_prompt(seed.category, index)
        negative_prompt = "readable text, letters, numbers, logos, watermark, captions"
        request = VisualImageRequest(
            card_id=card_id,
            visual_prompt=visual_prompt,
            negative_prompt=negative_prompt,
        )
        image = provider.generate(request) if provider is not None else _draft_image(request)
        cards.append(_card(model, card_id, seed, visual_prompt, negative_prompt, image))
    return {
        "schema_version": VISUAL_CARDS_SCHEMA_VERSION,
        "status": "ready",
        "provider": provider_name,
        "cards": cards,
        "assets": [card["image"] for card in cards],
    }


def _draft_image(request: VisualImageRequest) -> VisualImageMetadata:
    return {
        "provider": DRAFT_PROVIDER_NAME,
        "asset_path": "",
        "prompt": request.visual_prompt,
        "generated": False,
    }


def _card_seeds(model: ReportModel, source_text: str | None) -> list[_CardSeed]:
    seeds: list[_CardSeed] = []
    for section_index, section in enumerate(model.sections):
        seeds.extend(_section_seeds(section_index, section))
    if source_text:
        seeds.extend(_source_text_seeds(source_text))
    return seeds


def _section_seeds(section_index: int, section: Section) -> list[_CardSeed]:
    seeds: list[_CardSeed] = []
    for block_index, block in enumerate(section.blocks):
        for text in _block_texts(block):
            seeds.append(
                _CardSeed(
                    section_index=section_index,
                    block_index=block_index,
                    heading=section.heading,
                    text=text,
                    category=_seed_category(section.heading, text),
                )
            )
    return seeds


def _source_text_seeds(source_text: str) -> list[_CardSeed]:
    _, sections = parse_generic_markdown(source_text)
    seeds: list[_CardSeed] = []
    for section_index, section in enumerate(sections):
        seeds.extend(_section_seeds(_SOURCE_SECTION_OFFSET + section_index, section))
    return seeds


def _block_texts(block: Block) -> list[str]:
    if block.items:
        return [item.strip() for item in block.items if item.strip()]
    text = block.text.strip()
    return [text] if text else []


def _bounded_seeds(seeds: list[_CardSeed]) -> list[_CardSeed]:
    selected: list[_CardSeed] = []
    for category in _REQUIRED_CATEGORIES:
        seed = _first_seed_for_category(seeds, selected, category)
        if seed is not None:
            selected.append(seed)
    for seed in seeds:
        if len(selected) >= _MAX_CARDS:
            break
        if seed not in selected:
            selected.append(seed)
    while len(selected) < _MIN_CARDS:
        selected.append(seeds[len(selected) % len(seeds)])
    return selected


def _first_seed_for_category(
    seeds: list[_CardSeed],
    selected: list[_CardSeed],
    category: str,
) -> _CardSeed | None:
    for seed in seeds:
        if seed.category == category and seed not in selected:
            return seed
    return None


def _seed_category(heading: str, text: str) -> CardSeedCategory:
    heading_text = heading.strip()
    body_text = text.strip()
    for keyword, category in _CATEGORY_HEADINGS.items():
        if keyword in heading_text:
            return _card_seed_category(category)
    if re.search(r"리스크|위험|혼선|지연|대응", body_text):
        return "risk"
    if re.search(r"다음 액션|후속 조치|확정한다|측정한다|\\d{4}-\\d{2}-\\d{2}까지", body_text):
        return "next_action"
    if re.search(r"근거|지표|파일럿|평균|\\d+[%건곳]", body_text):
        return "evidence"
    if re.search(r"결정|권고|우선|출시|도입", body_text):
        return "decision"
    if heading_text in {"제안 요약", "개요", "목표"}:
        return "summary"
    return "context"


def _card_seed_category(category: str) -> CardSeedCategory:
    if category == "risk":
        return "risk"
    if category == "next_action":
        return "next_action"
    if category == "decision":
        return "decision"
    if category == "evidence":
        return "evidence"
    if category == "summary":
        return "summary"
    return "context"


def _card(
    model: ReportModel,
    card_id: str,
    seed: _CardSeed,
    visual_prompt: str,
    negative_prompt: str,
    image: VisualImageMetadata,
) -> VisualCardDict:
    return {
        "id": card_id,
        "title": _overlay_title(seed.heading),
        "body": _overlay_body(seed.text),
        "caption": f"출처: {seed.heading}",
        "visual_prompt": visual_prompt,
        "negative_prompt": negative_prompt,
        "source_refs": [
            {
                "source_plan_path": model.source_plan_path,
                "section": seed.section_index,
                "block": seed.block_index,
                "heading": seed.heading,
            }
        ],
        "image": image,
        "approved": False,
    }


def _overlay_title(heading: str) -> str:
    return heading.strip() or "핵심 카드"


def _overlay_body(text: str) -> str:
    return text.strip()[:140]


def _visual_prompt(category: CardSeedCategory, index: int) -> str:
    scenes = {
        "summary": "operations team reviewing a clean workflow board",
        "evidence": "manager comparing simple progress markers",
        "decision": "product team aligning decisions with customer journey cards",
        "risk": "risk review moment with calm checklist visuals",
        "next_action": "handoff scene with clear action lanes and warm paper texture",
        "context": "staff coordinating next steps around a shared desk",
    }
    scene = scenes.get(category, scenes["context"])
    prompt = f"2D business comic illustration, {scene}, editorial planning companion card, {NO_TEXT_PROMPT}"
    if _HANGUL_RE.search(prompt):
        return f"2D business comic illustration, abstract report companion scene, {NO_TEXT_PROMPT}"
    return prompt
