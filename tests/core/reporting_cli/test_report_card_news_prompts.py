from __future__ import annotations

from pathlib import Path

from vibelign.core.reporting_cli.report_card_news_prompts import (
    PROMPT_FILENAMES,
    write_card_news_prompt_pack,
)


def _card(number: int) -> dict:
    return {
        "id": f"c{number}", "title": f"카드 {number} 제목", "body": f"카드 {number} 본문", "caption": "출처: 개요",
        "visual_prompt": "scene, no readable text in image", "negative_prompt": "text",
        "source_refs": [], "approved": True,
        "image": {"provider": "agy", "asset_path": "", "prompt": "", "generated": False, "source": "template"},
    }


def _payload(cards: list[dict]) -> dict:
    return {"schema_version": "report-visual-cards-v1", "status": "ready", "provider": "agy", "cards": cards, "assets": []}


def test_image_prompts_request_one_separate_image_per_card(tmp_path: Path) -> None:
    cards = [_card(i) for i in range(1, 7)]  # 6 cards
    pack = write_card_news_prompt_pack(tmp_path, _payload(cards), cards)
    assert {p.name for p in pack.prompt_paths} == set(PROMPT_FILENAMES)

    for name in ("gemini-image-prompt.md", "chatgpt-image-prompt.md", "generic-prompt.md"):
        text = (tmp_path / name).read_text(encoding="utf-8")
        # Must tell the model how many separate images and to NOT combine them.
        assert "6" in text, f"{name} must state the card count"
        assert ("개별" in text) or ("separate" in text.lower()), f"{name} must ask for separate images"
        assert ("합치지" in text) or ("do not combine" in text.lower()) or ("not a single" in text.lower()), (
            f"{name} must forbid a single combined grid"
        )
        # The old single-image wording must be gone.
        assert "single-page" not in text
        assert "Create one Korean" not in text


def test_html_prompt_separates_each_card_within_a_single_file(tmp_path: Path) -> None:
    cards = [_card(i) for i in range(1, 7)]
    write_card_news_prompt_pack(tmp_path, _payload(cards), cards)
    html_prompt = (tmp_path / "claude-html-prompt.md").read_text(encoding="utf-8")
    # Still ONE self-contained HTML file (powers paste-into-Claude), but each card must be its
    # own standalone full section so print/PDF yields 6 separate pages — the HTML equivalent of
    # "separate images".
    assert "단일 HTML" in html_prompt
    assert "6" in html_prompt  # states the card count
    assert ("분리" in html_prompt) or ("독립" in html_prompt)
    assert ("page-break" in html_prompt) or ("한 페이지" in html_prompt)
