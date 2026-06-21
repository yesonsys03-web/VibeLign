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
    prompt_paths = [prompt_dir / filename for filename in PROMPT_FILENAMES]
    prompts = (
        _chatgpt_image_prompt(storyboard),
        _gemini_image_prompt(storyboard),
        _claude_html_prompt(storyboard),
        _generic_prompt(storyboard),
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


def _generic_prompt(storyboard: str) -> str:
    return f"""# 범용 카드뉴스 생성 프롬프트

아래 스토리보드 JSON을 바탕으로 초보자도 10초 안에 이해할 수 있는 한국어 카드뉴스를 만들어줘.

요구사항:
- 흰 종이, 검은 굵은 선, 빨강/파랑/노랑 포인트가 있는 손그림 인포그래픽 스타일
- 각 카드의 내용 칸에는 텍스트 없는 간단한 이미지/도식 영역을 넣기
- 한국어 본문은 정확하게 유지하고, 문장을 새로 길게 늘리지 않기
- 마지막 결과는 바로 이미지 생성 모델이나 HTML 생성 모델에 넘길 수 있게 정리하기

스토리보드 JSON:

```json
{storyboard}
```
"""


def _chatgpt_image_prompt(storyboard: str) -> str:
    return f"""# ChatGPT / OpenAI 이미지 생성용 프롬프트

Create one Korean educational card-news infographic from the storyboard JSON below.

Style:
- Hand-drawn white paper infographic
- Thick black outlines, warm paper background, red/blue/yellow accent marks
- Numbered cards with simple body illustrations, arrows, speech bubbles, underline marks
- Keep every Korean text short, large, and readable
- Use the storyboard text exactly; do not add long new Korean sentences
- If Korean text rendering is unreliable, prioritize clean layout and leave text areas clear for HTML overlay

Storyboard JSON:

```json
{storyboard}
```
"""


def _gemini_image_prompt(storyboard: str) -> str:
    return f"""# Gemini 이미지 생성용 프롬프트

Generate a single-page Korean card-news infographic using the storyboard JSON.

Visual direction:
- Simple Korean explainer poster, hand-drawn marker style
- White paper surface, bold black borders, strong numbered boxes
- Put a small text-free illustration or diagram inside each card body area
- Use red, blue, and yellow only as accents
- Preserve the Korean titles and bullet meanings from the storyboard
- Avoid tiny text, dense paragraphs, logos, watermarks, and photorealism

Storyboard JSON:

```json
{storyboard}
```
"""


def _claude_html_prompt(storyboard: str) -> str:
    return f"""# Claude HTML 생성용 프롬프트

아래 스토리보드 JSON으로 반응형 HTML 카드뉴스를 만들어줘.

조건:
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
