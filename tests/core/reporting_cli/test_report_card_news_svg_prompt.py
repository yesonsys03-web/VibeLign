from __future__ import annotations

from vibelign.core.reporting_cli.report_card_news_asset_generator import _svg_prompt
from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict


def _card() -> VisualCardDict:
    return {
        "id": "c1", "title": "예약 알림",
        "body": "캘린더 예약과 알림 권한 흐름을 한 장으로 설명합니다.",
        "caption": "출처: 개요",
        "visual_prompt": "mobile calendar reminder permission flow, no readable text in image",
        "negative_prompt": "readable text, logo, watermark",
        "source_refs": [],
        "image": {"provider": "agy", "asset_path": "", "prompt": "fallback prompt", "generated": False, "source": "template"},
        "approved": True,
    }


def test_svg_prompt_drops_minimalist_constraints() -> None:
    prompt = _svg_prompt(_card())
    assert "under 80 elements" not in prompt
    assert "geometric shapes only" not in prompt


def test_svg_prompt_requests_rich_illustration_and_keeps_safety_rules() -> None:
    prompt = _svg_prompt(_card())
    assert "detailed" in prompt.lower() or "rich" in prompt.lower()
    # 보안 불변식 문장 유지
    assert "<text>" in prompt
    assert "viewBox 0 0 320 150" in prompt
    # 카드 맥락 포함(기존 통합 테스트 호환)
    assert "calendar reminder permission" in prompt
