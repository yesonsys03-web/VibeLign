from __future__ import annotations

# === ANCHOR: REPORT_CARD_NEWS_PROMPTS_START ===
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict, VisualCardsDict

PROMPT_FILENAMES: Final = (
    "chatgpt-image-prompt.md",
    "gemini-image-prompt.md",
    "claude-html-prompt.md",
    "generic-prompt.md",
)


@dataclass(frozen=True, slots=True)
class CardNewsPromptPack:
    prompt_dir: Path
    prompt_paths: list[Path]


def write_card_news_prompt_pack(
    prompt_dir: Path,
    payload: VisualCardsDict,
    cards: list[VisualCardDict],
) -> CardNewsPromptPack:
    prompt_dir.mkdir(parents=True, exist_ok=True)
    storyboard = _storyboard_json(payload, cards)
    card_count = len(cards)
    prompt_paths = [prompt_dir / filename for filename in PROMPT_FILENAMES]
    prompts = (
        _chatgpt_image_prompt(storyboard, card_count),
        _gemini_image_prompt(storyboard, card_count),
        _claude_html_prompt(storyboard, card_count),
        _generic_prompt(storyboard, card_count),
    )
    for path, prompt in zip(prompt_paths, prompts, strict=True):
        _ = path.write_text(prompt, encoding="utf-8")
    return CardNewsPromptPack(prompt_dir=prompt_dir, prompt_paths=prompt_paths)


def _storyboard_json(payload: VisualCardsDict, cards: list[VisualCardDict]) -> str:
    data = {
        "schema_version": "report-card-news-storyboard-v1",
        "provider": payload["provider"],
        "cards": [
            {
                "number": index,
                "title": card["title"],
                "body": card["body"],
                "caption": card["caption"],
                "visual_prompt": card["visual_prompt"],
                "negative_prompt": card["negative_prompt"],
            }
            for index, card in enumerate(cards, 1)
        ],
        "style": {
            "layout": "Korean hand-drawn educational card news infographic",
            "text_policy": "Keep Korean text readable and editable; do not invent extra body copy.",
            "visual_policy": "Use text-free simple diagrams or illustrations inside each card body slot.",
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _generic_prompt(storyboard: str, card_count: int) -> str:
    return f"""# 범용 카드뉴스 생성 프롬프트 (카드별 개별 이미지)

아래 스토리보드 JSON에는 카드가 {card_count}장 있어. 카드마다 독립된 이미지 1장씩, 번호 순서(1→{card_count})대로 총 {card_count}장의 개별 이미지를 만들어줘.

반드시 지킬 것:
- {card_count}장을 하나의 페이지·그리드·콜라주로 합치지 마. 각 카드는 그 카드 하나만 담은 단독 이미지여야 해.
- 흰 종이, 검은 굵은 선, 빨강/파랑/노랑 포인트가 있는 손그림 인포그래픽 스타일
- 각 카드 왼쪽 위에 번호 배지를 넣고, 내용 칸에는 텍스트 없는 간단한 이미지/도식 영역을 넣기
- 한국어 본문은 정확하게 유지하고, 문장을 새로 길게 늘리지 않기

스토리보드 JSON:

```json
{storyboard}
```
"""


def _chatgpt_image_prompt(storyboard: str, card_count: int) -> str:
    return f"""# ChatGPT / OpenAI 이미지 생성용 프롬프트 (카드별 개별 이미지)

The storyboard JSON below has {card_count} cards. Generate {card_count} SEPARATE images — exactly one standalone image per card, in number order 1 to {card_count}.

Critical:
- Do NOT combine the cards into a single page, grid, collage, or poster. Each output is one independent square image containing only that one card.
- Return {card_count} distinct images, one per card, in order.

Each card image style:
- Hand-drawn white paper infographic, thick black outlines, warm paper background, red/blue/yellow accent marks
- A number badge top-left, the Korean title, and one simple text-free body illustration
- Keep every Korean text short, large, and readable; use the storyboard text exactly; do not add long new Korean sentences

Storyboard JSON:

```json
{storyboard}
```
"""


def _gemini_image_prompt(storyboard: str, card_count: int) -> str:
    return f"""# Gemini 이미지 생성용 프롬프트 (카드별 개별 이미지)

아래 스토리보드 JSON에는 카드가 {card_count}장 있어. 카드 1장당 독립된(separate) 이미지 1장씩, 번호 순서(1→{card_count})대로 총 {card_count}장의 개별 이미지를 생성해줘. (Gemini는 한 응답에 여러 장의 이미지를 낼 수 있어 — {card_count}장을 각각 따로 내보내.)

매우 중요 (반드시 지킬 것):
- {card_count}장을 하나의 페이지·그리드·콜라주·포스터로 합치지 마(do not combine into one image). 각 이미지는 그 카드 하나만 담은 정사각형 단독 이미지여야 해.
- 최종 출력은 {card_count}개의 분리된 이미지여야 하고, 번호 순서대로 1장씩.

각 카드 이미지 스타일:
- 손그림 마커 스타일, 흰 종이, 굵은 검은 테두리, 왼쪽 위 번호 배지
- 카드 제목(한국어)과 본문 의미를 살린 텍스트 없는 간단한 일러스트/도식 1개
- 빨강·파랑·노랑은 포인트로만. 작은 글씨, 빽빽한 문단, 로고, 워터마크, 사진풍 금지

스토리보드 JSON:

```json
{storyboard}
```
"""


def _claude_html_prompt(storyboard: str, card_count: int) -> str:
    return f"""# Claude HTML 생성용 프롬프트 (카드별 분리)

아래 스토리보드 JSON으로 반응형 HTML 카드뉴스를 만들어줘. 카드는 {card_count}장이고, 각 카드를 독립된 전체 카드 1장으로 분리해서 번호 순서(1→{card_count})대로 보여줘.

조건:
- 카드 {card_count}장을 한 화면에 빽빽이 몰아넣지 말고, 카드마다 화면을 꽉 채우는 독립 섹션으로 구성해. 인쇄/PDF 저장 시 카드 1장당 한 페이지가 되도록 각 카드 사이에 페이지 나눔(break-after: page; 한 페이지 한 카드)을 적용해.
- 한국어 텍스트는 DOM 텍스트로 렌더링해서 수정 가능해야 함
- 각 카드의 내용 칸 안에 이미지/도식 슬롯을 넣고, 실제 이미지가 없으면 CSS 도형으로 대체
- 흰 종이, 굵은 검은 테두리, 손그림풍 강조선, 번호 배지를 사용
- 외부 스크립트, 외부 이미지, CDN 없이 단일 HTML로 동작
- 모바일에서도 텍스트가 겹치거나 잘리지 않게 구성

스토리보드 JSON:

```json
{storyboard}
```
"""


# === ANCHOR: REPORT_CARD_NEWS_PROMPTS_END ===
