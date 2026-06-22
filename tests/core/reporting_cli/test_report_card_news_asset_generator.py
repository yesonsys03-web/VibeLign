from __future__ import annotations

from pathlib import Path
from threading import Lock
from time import sleep

import pytest

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.reporting_cli.report_card_news_asset_generator import (
    CardNewsAssetError,
    materialize_card_news_assets,
)
from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict


class FakeRunner:
    def __init__(self, stdout: str, status: cli_adapters.PlanningCliStatus = "ok") -> None:
        self.stdout: str = stdout
        self.status: cli_adapters.PlanningCliStatus = status
        self.commands: list[list[str]] = []

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    ) -> cli_adapters.PlanningCliResult:
        _ = cwd
        _ = input_text
        _ = timeout_seconds
        self.commands.append(command)
        return cli_adapters.PlanningCliResult(
            status=self.status,
            stdout=self.stdout,
            stderr="",
            exit_code=0,
            duration_ms=7,
        )


class CountingRunner:
    def __init__(self, stdout: str) -> None:
        self.stdout: str = stdout
        self.commands: list[list[str]] = []
        self._active = 0
        self.max_active = 0
        self._lock = Lock()

    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    ) -> cli_adapters.PlanningCliResult:
        _ = cwd
        _ = input_text
        _ = timeout_seconds
        with self._lock:
            self.commands.append(command)
            self._active += 1
            self.max_active = max(self.max_active, self._active)
        sleep(0.02)
        with self._lock:
            self._active -= 1
        return cli_adapters.PlanningCliResult(
            status="ok",
            stdout=self.stdout,
            stderr="",
            exit_code=0,
            duration_ms=7,
        )


def _card(provider: str = "provider-neutral-draft") -> VisualCardDict:
    return {
        "id": "card-1",
        "title": "예약 알림",
        "body": "캘린더 예약과 알림 권한 흐름을 한 장으로 설명합니다.",
        "caption": "출처: 개요",
        "visual_prompt": "mobile calendar reminder permission flow with push notification toggle, no readable text in image",
        "negative_prompt": "readable text, logo, watermark",
        "source_refs": [{"source_plan_path": "plans/demo.md", "section": 0, "block": 0, "heading": "개요"}],
        "image": {
            "provider": provider,
            "asset_path": "",
            "prompt": "mobile calendar reminder permission flow with push notification toggle, no readable text in image",
            "generated": False,
            "source": "template",
        },
        "approved": True,
    }


def _card_with_id(card_id: str, title: str, provider: str = "opencode") -> VisualCardDict:
    card = _card(provider)
    return {
        **card,
        "id": card_id,
        "title": title,
        "visual_prompt": f"{title} specific visual prompt, no readable text in image",
        "image": {
            "provider": provider,
            "asset_path": "",
            "prompt": f"{title} specific visual prompt, no readable text in image",
            "generated": False,
            "source": "template",
        },
    }


def _fake_build_command(provider: str, prompt: str) -> list[str]:
    return ["fake", provider, prompt]


def test_model_provider_generates_svg_asset_from_visual_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner('<svg viewBox="0 0 320 150" data-model="opencode"><rect width="320" height="150"/></svg>')
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("opencode")], runner=runner)

    asset_path = tmp_path / cards[0]["image"]["asset_path"]
    svg = asset_path.read_text(encoding="utf-8")
    assert cards[0]["image"]["generated"] is True
    assert cards[0]["image"]["provider"] == "opencode"
    assert 'data-model="opencode"' in svg
    assert 'data-schema="report-card-news-svg-asset-v1"' in svg
    assert "data-sketch-symbols" not in svg
    assert "calendar reminder permission" in runner.commands[0][2]
    assert cards[0]["image"]["source"] == "llm"


def test_model_provider_reuses_existing_asset_without_cli_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner('<svg viewBox="0 0 320 150" data-model="opencode"><rect width="320" height="150"/></svg>')
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    first_cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("opencode")], runner=runner)
    asset_path = tmp_path / first_cards[0]["image"]["asset_path"]
    original_svg = asset_path.read_text(encoding="utf-8")
    second_runner = FakeRunner('<svg viewBox="0 0 320 150" data-model="changed"><circle cx="20" cy="20" r="10"/></svg>')

    second_cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("opencode")], runner=second_runner)

    assert second_runner.commands == []
    assert second_cards[0]["image"]["asset_path"] == first_cards[0]["image"]["asset_path"]
    assert asset_path.read_text(encoding="utf-8") == original_svg


def test_model_provider_generates_multiple_assets_concurrently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CountingRunner('<svg viewBox="0 0 320 150"><rect width="320" height="150"/></svg>')
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    cards = [_card_with_id(f"card-{index}", f"카드 {index}") for index in range(1, 4)]

    generated_cards = materialize_card_news_assets(tmp_path, "예약-알림", cards, runner=runner)

    assert len(generated_cards) == 3
    assert len(runner.commands) == 3
    assert runner.max_active > 1


def test_model_provider_falls_back_to_local_asset_when_cli_times_out(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner("", status="timeout")
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("claude")], runner=runner, timeout_seconds=1)

    asset_path = tmp_path / cards[0]["image"]["asset_path"]
    svg = asset_path.read_text(encoding="utf-8")
    assert cards[0]["image"]["generated"] is True
    assert cards[0]["image"]["provider"] == "claude"
    assert "data-sketch-symbols" in svg
    assert len(runner.commands) == 1
    assert cards[0]["image"]["source"] == "fallback"


def test_model_provider_rejects_unsafe_svg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner('<svg viewBox="0 0 320 150"><script>alert(1)</script></svg>')
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    with pytest.raises(CardNewsAssetError):
        _ = materialize_card_news_assets(tmp_path, "예약-알림", [_card("codex")], runner=runner)


def test_model_provider_strips_readable_svg_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner('<svg viewBox="0 0 320 150"><text x="10" y="20">Alarm</text><circle cx="80" cy="80" r="20"/></svg>')
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("claude")], runner=runner)

    svg = (tmp_path / cards[0]["image"]["asset_path"]).read_text(encoding="utf-8")
    assert "<text" not in svg
    assert "Alarm" not in svg
    assert "<circle" in svg


def test_model_provider_allows_standard_svg_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 150"><rect width="320" height="150"/></svg>')
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("opencode")], runner=runner)

    svg = (tmp_path / cards[0]["image"]["asset_path"]).read_text(encoding="utf-8")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert '<rect width="320" height="150"' in svg


def test_non_cli_provider_marks_source_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner("")
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("provider-neutral-draft")], runner=runner)

    assert cards[0]["image"]["source"] == "template"
    assert runner.commands == []
