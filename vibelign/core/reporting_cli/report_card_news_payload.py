# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_START ===
from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

from vibelign.core.reporting_cli.report_visual_cards import (
    VISUAL_CARDS_SCHEMA_VERSION,
    VisualCardDict,
    VisualCardsDict,
    VisualCardSourceRef,
)


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_CARDNEWSPAYLOADERROR_START ===
class CardNewsPayloadError(ValueError):
    pass
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_CARDNEWSPAYLOADERROR_END ===


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__SOURCEREFMODEL_START ===
class _SourceRefModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    source_plan_path: str = ""
    section: int = 0
    block: int = 0
    heading: str = ""
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__SOURCEREFMODEL_END ===


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__IMAGEMODEL_START ===
class _ImageModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    provider: str = ""
    asset_path: str = ""
    prompt: str = ""
    generated: StrictBool = False
    source: Literal["llm", "fallback", "template"] = "template"
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__IMAGEMODEL_END ===


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__CARDMODEL_START ===
class _CardModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: str = ""
    title: str = "카드"
    body: str = ""
    caption: str = ""
    visual_prompt: str = ""
    negative_prompt: str = ""
    source_refs: list[_SourceRefModel] = Field(default_factory=list)
    image: _ImageModel = Field(default_factory=_ImageModel)
    approved: StrictBool = False
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__CARDMODEL_END ===


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__PAYLOADMODEL_START ===
class _PayloadModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    schema_version: str
    status: Literal["ready", "empty"] = "ready"
    provider: str = "generic-image-provider"
    cards: list[_CardModel]
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__PAYLOADMODEL_END ===


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_LOAD_VISUAL_CARDS_PAYLOAD_START ===
def load_visual_cards_payload(payload_path: Path) -> VisualCardsDict:
    try:
        model = _PayloadModel.model_validate_json(payload_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        raise CardNewsPayloadError(f"카드뉴스 payload를 읽을 수 없어요: {exc}") from exc
    if model.schema_version != VISUAL_CARDS_SCHEMA_VERSION:
        raise CardNewsPayloadError("카드뉴스 payload schema_version이 맞지 않아요.")
    return {
        "schema_version": VISUAL_CARDS_SCHEMA_VERSION,
        "status": model.status,
        "provider": model.provider or "generic-image-provider",
        "cards": [_card_from_model(card) for card in model.cards],
        "assets": [],
    }
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_LOAD_VISUAL_CARDS_PAYLOAD_END ===


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__CARD_FROM_MODEL_START ===
def _card_from_model(card: _CardModel) -> VisualCardDict:
    return {
        "id": card.id,
        "title": card.title or "카드",
        "body": card.body,
        "caption": card.caption,
        "visual_prompt": card.visual_prompt,
        "negative_prompt": card.negative_prompt,
        "source_refs": [_source_ref_from_model(ref) for ref in card.source_refs],
        "image": {
            "provider": card.image.provider,
            "asset_path": card.image.asset_path,
            "prompt": card.image.prompt,
            "generated": card.image.generated,
            "source": card.image.source,
        },
        "approved": card.approved is True,
    }
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__CARD_FROM_MODEL_END ===


# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__SOURCE_REF_FROM_MODEL_START ===
def _source_ref_from_model(ref: _SourceRefModel) -> VisualCardSourceRef:
    return {
        "source_plan_path": ref.source_plan_path,
        "section": ref.section,
        "block": ref.block,
        "heading": ref.heading,
    }
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD__SOURCE_REF_FROM_MODEL_END ===
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_END ===
