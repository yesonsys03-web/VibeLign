# === ANCHOR: REPORT_VISUAL_CARDS_CLI_START ===
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeAlias

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.response_policy import safe_planning_status
from vibelign.core.reporting_cli.report_visual_cards import (
    NO_TEXT_PROMPT,
    VisualCardDict,
    VisualCardsDict,
    VisualImageMetadata,
)

_JSON_BLOCK_RE: Final[re.Pattern[str]] = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_MAX_SOURCE_CHARS: Final = 7000
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
# === ANCHOR: REPORT_VISUAL_CARDS_CLI_VISUALCARDSCLIERROR_START ===
class VisualCardsCliError(RuntimeError):
    provider: str
    reason: str

    # === ANCHOR: REPORT_VISUAL_CARDS_CLI___STR___START ===
    def __str__(self) -> str:
# === ANCHOR: REPORT_VISUAL_CARDS_CLI_VISUALCARDSCLIERROR_END ===
        return f"{self.provider} CLI 카드뉴스 초안 생성 실패: {self.reason}"
    # === ANCHOR: REPORT_VISUAL_CARDS_CLI___STR___END ===


@dataclass(frozen=True, slots=True)
# === ANCHOR: REPORT_VISUAL_CARDS_CLI_CLIVISUALCARDSPROVIDER_START ===
class CliVisualCardsProvider:
    provider: str
    root: Path
    runner: cli_adapters.PlanningCliRunner | None = None
    timeout_seconds: int = 120

    # === ANCHOR: REPORT_VISUAL_CARDS_CLI_DRAFT_START ===
    def draft(self, base: VisualCardsDict, source_text: str) -> VisualCardsDict:
        if base["status"] == "empty":
            return {**base, "provider": self.provider}
        command = cli_adapters.build_cli_command(self.provider, _prompt(base, source_text))
        if command is None:
            raise VisualCardsCliError(self.provider, "CLI 실행 파일을 찾을 수 없어요.")
        runner = self.runner or cli_adapters.SubprocessPlanningCliRunner()
        result = runner.run(command, cwd=self.root, input_text="", timeout_seconds=self.timeout_seconds)
        status = safe_planning_status(result.status, result.stdout)
        if status != "ok":
            raise VisualCardsCliError(self.provider, result.stderr.strip() or status)
        payload = _parse_json_object(result.stdout)
        if payload is None:
            raise VisualCardsCliError(self.provider, "JSON 객체를 읽지 못했어요.")
        cards = _cards_from_payload(payload, base["cards"], self.provider)
        if not cards:
            raise VisualCardsCliError(self.provider, "카드 배열이 비어 있어요.")
        return {
            "schema_version": base["schema_version"],
            "status": "ready",
            "provider": self.provider,
            "cards": cards,
            "assets": [card["image"] for card in cards],
# === ANCHOR: REPORT_VISUAL_CARDS_CLI_CLIVISUALCARDSPROVIDER_END ===
        }
    # === ANCHOR: REPORT_VISUAL_CARDS_CLI_DRAFT_END ===


# === ANCHOR: REPORT_VISUAL_CARDS_CLI__PROMPT_START ===
def _prompt(base: VisualCardsDict, source_text: str) -> str:
    base_json = json.dumps({"cards": base["cards"]}, ensure_ascii=False)
    source = source_text[:_MAX_SOURCE_CHARS]
    return (
        "한국어 보고서 카드뉴스 초안을 더 이해하기 쉬운 카드뉴스 JSON으로 다시 작성하세요.\n"
        "원문에 없는 사실, 숫자, 일정, 담당자, 성과를 만들지 마세요.\n"
        "각 카드는 짧은 한국어 title, body, caption을 가져야 합니다.\n"
        "visual_prompt는 영어로만 작성하고 실제 이미지 안에는 글자가 없어야 하므로 no readable text in image를 포함하세요.\n"
        "응답은 설명 없이 JSON 객체 하나만 반환하세요.\n"
        '{"cards":[{"id":"report-card-1","title":"...","body":"...","caption":"출처: ...","visual_prompt":"..."}]}\n\n'
        f"기존 카드 JSON:\n{base_json}\n\n"
        f"원문:\n{source}"
    )
# === ANCHOR: REPORT_VISUAL_CARDS_CLI__PROMPT_END ===


# === ANCHOR: REPORT_VISUAL_CARDS_CLI__PARSE_JSON_OBJECT_START ===
def _parse_json_object(stdout: str) -> JsonObject | None:
    text = stdout.strip()
    candidates = [text]
    candidates.extend(match.group(1).strip() for match in _JSON_BLOCK_RE.finditer(text))
    if "{" in text and "}" in text:
        candidates.append(text[text.find("{"): text.rfind("}") + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            return value
    return None
# === ANCHOR: REPORT_VISUAL_CARDS_CLI__PARSE_JSON_OBJECT_END ===


# === ANCHOR: REPORT_VISUAL_CARDS_CLI__CARDS_FROM_PAYLOAD_START ===
def _cards_from_payload(payload: JsonObject, base_cards: list[VisualCardDict], provider: str) -> list[VisualCardDict]:
    raw_cards = payload.get("cards")
    if not isinstance(raw_cards, list):
        return []
    cards: list[VisualCardDict] = []
    for index, base_card in enumerate(base_cards[: len(raw_cards)]):
        raw_card = raw_cards[index]
        candidate = raw_card if isinstance(raw_card, dict) else {}
        title = _short_text(candidate.get("title"), base_card["title"], 36)
        body = _short_text(candidate.get("body"), base_card["body"], 150)
        caption = _short_text(candidate.get("caption"), base_card["caption"], 60)
        visual_prompt = _visual_prompt(candidate.get("visual_prompt"), base_card["visual_prompt"])
        image: VisualImageMetadata = {
            "provider": provider,
            "asset_path": "",
            "prompt": visual_prompt,
            "generated": False,
        }
        cards.append(
            {
                "id": base_card["id"],
                "title": title,
                "body": body,
                "caption": caption,
                "visual_prompt": visual_prompt,
                "negative_prompt": base_card["negative_prompt"],
                "source_refs": base_card["source_refs"],
                "image": image,
                "approved": False,
            }
        )
    return cards
# === ANCHOR: REPORT_VISUAL_CARDS_CLI__CARDS_FROM_PAYLOAD_END ===


# === ANCHOR: REPORT_VISUAL_CARDS_CLI__SHORT_TEXT_START ===
def _short_text(value: JsonValue | None, fallback: str, limit: int) -> str:
    text = value.strip() if isinstance(value, str) else ""
    return (text or fallback).strip()[:limit]
# === ANCHOR: REPORT_VISUAL_CARDS_CLI__SHORT_TEXT_END ===


# === ANCHOR: REPORT_VISUAL_CARDS_CLI__VISUAL_PROMPT_START ===
def _visual_prompt(value: JsonValue | None, fallback: str) -> str:
    text = value.strip() if isinstance(value, str) else ""
    if not text or re.search(r"[가-힣]", text):
        return fallback
    if NO_TEXT_PROMPT in text:
        return text[:260]
    return f"{text[:220]}, {NO_TEXT_PROMPT}"
# === ANCHOR: REPORT_VISUAL_CARDS_CLI__VISUAL_PROMPT_END ===
# === ANCHOR: REPORT_VISUAL_CARDS_CLI_END ===
