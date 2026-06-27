from __future__ import annotations

import re
from pathlib import Path

import pytest

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.reader import parse_plan_markdown
from vibelign.core.reporting_cli.report_visual_cards import (
    NO_TEXT_PROMPT,
    VisualImageMetadata,
    VisualImageRequest,
    build_report_visual_cards,
)
from vibelign.core.reporting_cli.report_visual_cards_cli import CliVisualCardsProvider
from vibelign.core.reporting_cli.templates import build_report_model


class RecordingProvider:
    provider_name = "test-fake-provider"

    def __init__(self) -> None:
        self.requests: list[VisualImageRequest] = []

    def generate(self, request: VisualImageRequest) -> VisualImageMetadata:
        self.requests.append(request)
        return {
            "provider": self.provider_name,
            "asset_path": f"fake://tests/{request.card_id}.png",
            "prompt": request.visual_prompt,
            "generated": False,
        }


def _model():
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "reporting_cli" / "quality_complete.md"
    data = parse_plan_markdown(fixture.read_text(encoding="utf-8"))
    return build_report_model(
        data,
        "proposal",
        date="2026-06-20",
        source_plan_path="plans/quality_complete.md",
    )


def _fixture_text() -> str:
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "reporting_cli" / "quality_complete.md"
    return fixture.read_text(encoding="utf-8")


def _category_model() -> ReportModel:
    return ReportModel(
        title="Category prompt regression",
        report_type="proposal",
        date="2026-06-20",
        source_plan_path="plans/category_prompt.md",
        sections=[
            Section("요약", [Block("paragraph", "전체 방향을 정리한다.")]),
            Section("근거", [Block("paragraph", "파일럿 지표를 비교한다.")]),
            Section("결정", [Block("paragraph", "우선순위를 결정한다.")]),
            Section("리스크", [Block("paragraph", "혼선과 지연 가능성을 점검한다.")]),
            Section("다음 액션", [Block("paragraph", "다음 액션을 확정한다.")]),
            Section("배경", [Block("paragraph", "현장의 맥락을 공유한다.")]),
        ],
    )


def test_visual_cards_build_three_to_six_source_backed_drafts():
    sidecar = build_report_visual_cards(_model(), source_text=_fixture_text())

    cards = sidecar["cards"]
    assert sidecar["schema_version"] == "report-visual-cards-v1"
    assert sidecar["provider"] == "provider-neutral-draft"
    assert 3 <= len(cards) <= 6
    assert all(card["source_refs"] for card in cards)
    assert all(card["image"]["provider"] == "provider-neutral-draft" for card in cards)
    assert all(card["image"]["asset_path"] == "" for card in cards)
    assert all(card["image"]["generated"] is False for card in cards)


def test_visual_cards_use_explicit_fake_provider_at_adapter_boundary():
    provider = RecordingProvider()

    sidecar = build_report_visual_cards(_model(), provider, source_text=_fixture_text())

    cards = sidecar["cards"]
    assert sidecar["provider"] == "test-fake-provider"
    assert len(provider.requests) == len(cards)
    assert all(card["image"]["provider"] == "test-fake-provider" for card in cards)
    assert all(card["image"]["asset_path"].startswith("fake://tests/") for card in cards)


def test_visual_cards_cli_provider_rewrites_card_copy_and_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRunner:
        def run(
            self,
            command: list[str],
            *,
            cwd: Path,
            input_text: str,
            timeout_seconds: int,
        ) -> cli_adapters.PlanningCliResult:
            return cli_adapters.PlanningCliResult(
                status="ok",
                stdout='{"cards":[{"id":"report-card-1","title":"예약 흐름","body":"예약 캘린더와 알림 문자를 한눈에 정리합니다.","caption":"출처: 핵심 기능","visual_prompt":"calendar reminder app screen with checklist, no readable text in image"}]}',
                stderr="",
                exit_code=0,
                duration_ms=12,
            )

    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda provider, prompt: ["fake", provider, prompt])
    base = build_report_visual_cards(_model(), source_text=_fixture_text())
    provider = CliVisualCardsProvider("opencode", root=tmp_path, runner=FakeRunner())

    sidecar = provider.draft(base, _fixture_text())

    assert sidecar["provider"] == "opencode"
    assert len(sidecar["cards"]) == 1
    assert len(sidecar["assets"]) == 1
    assert sidecar["cards"][0]["title"] == "예약 흐름"
    assert sidecar["cards"][0]["image"]["provider"] == "opencode"
    assert sidecar["cards"][0]["image"]["prompt"].startswith("calendar reminder app")


def test_visual_prompts_never_embed_korean_report_copy():
    sidecar = build_report_visual_cards(_model(), RecordingProvider(), source_text=_fixture_text())

    for card in sidecar["cards"]:
        assert NO_TEXT_PROMPT in card["visual_prompt"]
        assert re.search(r"[가-힣]", card["title"])
        assert re.search(r"[가-힣]", card["body"])
        assert re.search(r"[가-힣]", card["caption"])
        assert re.search(r"[가-힣]", card["visual_prompt"]) is None
        assert card["title"] not in card["visual_prompt"]
        assert card["body"] not in card["visual_prompt"]


def test_visual_cards_include_risk_and_next_action_when_source_has_them():
    sidecar = build_report_visual_cards(_model(), RecordingProvider(), source_text=_fixture_text())

    card_text = "\n".join(f"{card['title']}\n{card['body']}" for card in sidecar["cards"])
    risk_prompts = [
        card["visual_prompt"]
        for card in sidecar["cards"]
        if "리스크" in card["title"]
    ]
    next_action_prompts = [
        card["visual_prompt"]
        for card in sidecar["cards"]
        if "다음 액션" in card["title"]
    ]
    other_prompts = [
        card["visual_prompt"]
        for card in sidecar["cards"]
        if "리스크" not in card["title"] and "다음 액션" not in card["title"]
    ]
    assert "리스크" in card_text
    assert "다음 액션" in card_text
    assert "근거" in card_text or "지표" in card_text
    assert risk_prompts
    assert next_action_prompts
    assert risk_prompts[0] != next_action_prompts[0]
    assert risk_prompts[0] not in other_prompts
    assert next_action_prompts[0] not in other_prompts


def test_draft_image_marks_source_template() -> None:
    built = build_report_visual_cards(_category_model())
    assert built["cards"][0]["image"]["source"] == "template"


def test_visual_prompts_keep_category_scenes_without_provider_or_korean_leakage():
    sidecar = build_report_visual_cards(_category_model())

    prompts_by_title = {card["title"]: card["visual_prompt"] for card in sidecar["cards"]}
    prompt_text = "\n".join(prompts_by_title.values())
    assert set(prompts_by_title) == {"요약", "근거", "결정", "리스크", "다음 액션", "배경"}
    assert len(set(prompts_by_title.values())) == len(prompts_by_title)
    assert all(NO_TEXT_PROMPT in prompt for prompt in prompts_by_title.values())
    assert prompts_by_title["리스크"] != prompts_by_title["요약"]
    assert prompts_by_title["리스크"] != prompts_by_title["배경"]
    assert prompts_by_title["다음 액션"] != prompts_by_title["요약"]
    assert prompts_by_title["다음 액션"] != prompts_by_title["배경"]
    assert re.search(r"[가-힣]", prompt_text) is None
    assert "Korean" not in prompt_text
    assert "imagen2" not in prompt_text.lower()
    assert "fake" not in prompt_text.lower()
    assert "fake://" not in prompt_text
    assert "test-fake-provider" not in prompt_text
